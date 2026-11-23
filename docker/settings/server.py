# SPDX-FileCopyrightText: 2026 Akvorado contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Local administration for an Akvorado installation using Caddy and Compose."""

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socketserver
import stat
import subprocess
import tempfile
import threading
from urllib.parse import unquote, urlsplit

ENDPOINT = "/api/v0/console/settings"
CLIENT_NAMES = ENDPOINT + "/client-names"
AUTH_HEADER = "X-Akvorado-Settings-User"
USER = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}"
BCRYPT = r"\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}"
AUTH_BLOCK = re.compile(r"^([ \t]+)basic_auth \{\n(?P<users>.*?)^\1\}", re.MULTILINE | re.DOTALL)
TABLES = {
    "flows": ("0", "Raw flows"),
    "flows_1m0s": ("1m", "1-minute rollups"),
    "flows_5m0s": ("5m", "5-minute rollups"),
    "flows_1h0m0s": ("1h", "1-hour rollups"),
}
TTL = re.compile(r"\bTTL\s+TimeReceived\s*\+\s*toIntervalSecond\((\d+)\)")
DAY = 86400


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def run(*args, data=None):
    return subprocess.run(
        args, input=data, capture_output=True, timeout=15, check=True,
    ).stdout.decode("utf-8").strip()


def replace_in_place(path, content):
    # Caddy mounts the config file itself, so keep the inode on updates.
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def write_config(path, content):
    metadata = path.stat() if path.exists() else None
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False,
    ) as file:
        temporary = Path(file.name)
        try:
            if metadata is not None:
                os.fchown(file.fileno(), metadata.st_uid, metadata.st_gid)
                os.fchmod(file.fileno(), stat.S_IMODE(metadata.st_mode))
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def named_auth_block(content):
    matches = list(AUTH_BLOCK.finditer(content))
    if len(matches) != 1:
        raise RuntimeError("Expected one bcrypt authentication block")
    block = matches[0]
    accounts = {}
    for line in block["users"].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        entry = re.fullmatch(rf"\s*({USER})\s+({BCRYPT})\s*", line)
        if not entry or entry[1] in accounts:
            raise RuntimeError("Unexpected Caddy account entry")
        accounts[entry[1]] = entry[2]
    return block, accounts


def retention_scalars(content):
    """Locate the TTL scalar for each supported resolution in the Compose config."""
    root = re.search(r"(?m)^clickhouse:[ \t]*(?:#[^\n]*)?$", content)
    if not root:
        return {}
    rest = content[root.end():]
    end = re.search(r"(?m)^\S", rest)
    section = rest[:end.start()] if end else rest
    block = re.search(
        r"(?m)^  resolutions:[ \t]*(?:#[^\n]*)?\n"
        r"(?P<items>(?:^(?:    [^\n]+|[ \t]*(?:#[^\n]*)?)\n)+)",
        section,
    )
    if not block:
        return {}
    items = block["items"]
    starts = list(re.finditer(r"(?m)^    - interval: ([^\s#]+)[ \t]*(?:#[^\n]*)?$", items))
    slots = {}
    for index, start in enumerate(starts):
        interval = start[1]
        next_item = starts[index + 1].start() if index + 1 < len(starts) else len(items)
        ttl = re.search(r"(?m)^      ttl: (\d+h|0s)[ \t]*(?:#[^\n]*)?$", items[start.end():next_item])
        if not ttl or interval in slots:
            continue
        offset = root.end() + block.start("items") + start.end()
        slots[interval] = (offset + ttl.start(1), offset + ttl.end(1), ttl[1])
    return slots


class Settings:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()

    def caddy(self, *args, data=None):
        return run("docker", "exec", "-i", self.args.caddy, "caddy", *args, data=data)

    def clickhouse(self, query):
        return run(
            "docker", "exec", self.args.clickhouse, "clickhouse-client",
            "--database", self.args.database, "--query", query,
        )

    def reload_caddy(self):
        run("docker", "kill", "--signal=USR1", self.args.caddy)

    def change_user(self, method, username, body):
        if not isinstance(username, str) or not re.fullmatch(USER, username):
            raise RequestError(400, "Use 1–32 letters, digits, dots, dashes or underscores for the username.")
        path = self.args.caddyfile
        old = path.read_text(encoding="utf-8")
        block, accounts = named_auth_block(old)
        if self.args.admin not in accounts:
            raise RuntimeError("Configured administrator is missing")
        if method == "POST" and username in accounts:
            raise RequestError(409, "This username already exists.")
        if method != "POST" and username not in accounts:
            raise RequestError(404, "This user no longer exists.")
        entries = block["users"]
        if method == "DELETE":
            if username == self.args.admin:
                raise RequestError(403, "The administrator account cannot be removed.")
            entries = re.sub(rf"(?m)^\s*{re.escape(username)}[ \t]+{BCRYPT}[ \t]*\n", "", entries)
        else:
            password = body.get("password")
            if not isinstance(password, str) or not 12 <= len(password.encode("utf-8")) <= 72 or any(c in password for c in "\r\n\x00"):
                raise RequestError(400, "Enter a password of 12–72 bytes without line breaks.")
            digest = self.caddy(
                "hash-password", "--algorithm", "bcrypt", "--bcrypt-cost", "12",
                data=password.encode("utf-8"),
            )
            if not re.fullmatch(BCRYPT, digest):
                raise RuntimeError("Unexpected password hash")
            if method == "POST":
                entries += f"{block[1]}  {username} {digest}\n"
            else:
                entries = re.sub(rf"(?m)^(\s*{re.escape(username)}[ \t]+){BCRYPT}", rf"\g<1>{digest}", entries)
        new = old[:block.start("users")] + entries + old[block.end("users"):]
        self.caddy("validate", "--config", "-", "--adapter", "caddyfile", data=new.encode("utf-8"))
        if path.read_text(encoding="utf-8") != old:
            raise RequestError(409, "The proxy configuration changed. Reload Settings and try again.")
        try:
            replace_in_place(path, new)
            self.reload_caddy()
        except (OSError, subprocess.SubprocessError):
            replace_in_place(path, old)
            self.reload_caddy()
            raise
        return {"message": "User updated."}

    def retention(self, config):
        # Read effective TTL before deciding whether the persisted setting can be edited.
        names = ", ".join(f"'{table}'" for table in TABLES)
        raw = self.clickhouse(
            f"SELECT name, engine, create_table_query FROM system.tables "
            f"WHERE database=currentDatabase() AND name IN ({names}) FORMAT JSONEachRow",
        )
        columns = {row["name"]: row for row in map(json.loads, raw.splitlines())}
        slots = retention_scalars(config)
        values = []
        for table, (interval, label) in TABLES.items():
            if table not in columns:
                continue
            row = columns[table]
            match = TTL.search(row["create_table_query"])
            seconds = int(match[1]) if match else None
            days = seconds // DAY if seconds is not None and seconds % DAY == 0 else None
            recognized = seconds is not None or "TTL " not in row["create_table_query"]
            setting = slots.get(interval)
            configured = ("0s" if seconds is None else f"{seconds // 3600}h")
            editable = bool(
                recognized and (seconds is None or days is not None)
                and row["engine"] in ("MergeTree", "SummingMergeTree")
                and setting and setting[2] == configured
            )
            values.append({"table": table, "label": label, "days": days, "editable": editable})
        return values

    def change_retention(self, body):
        table = body.get("table")
        days = body.get("days")
        expected = body.get("expectedDays")
        if (
            not isinstance(table, str) or table not in TABLES
            or type(days) is not int or not 1 <= days <= 3650
            or (expected is not None and type(expected) is not int)
        ):
            raise RequestError(400, "Choose a retention period of 1–3650 days.")
        path = self.args.config
        old = path.read_text(encoding="utf-8")
        item = next((row for row in self.retention(old) if row["table"] == table), None)
        if not item or not item["editable"]:
            raise RequestError(409, "This retention policy is managed outside Settings.")
        current = item["days"]
        if current != expected:
            raise RequestError(409, "Retention has changed. Reload Settings and try again.")
        if current == days:
            return {"message": "Retention is already set."}
        if (current is None or days < current) and body.get("confirmReduction") is not True:
            raise RequestError(409, "Confirm the retention reduction before saving.")
        start, end, _ = retention_scalars(old)[TABLES[table][0]]
        candidate = old[:start] + f"{days * 24}h" + old[end:]
        if path.read_text(encoding="utf-8") != old:
            raise RequestError(409, "The data configuration changed. Reload Settings and try again.")
        write_config(path, candidate)
        try:
            self.clickhouse(
                f"ALTER TABLE {table} MODIFY TTL TimeReceived + toIntervalSecond({days * DAY}) "
                "SETTINGS materialize_ttl_after_modify=0"
            )
        except (OSError, subprocess.SubprocessError):
            write_config(path, old)
            raise
        logging.info("Updated retention for %s from %s to %s days", table, current, days)
        return {"message": "Retention updated."}

    @property
    def names_file(self):
        return Path(os.environ.get("STATE_DIRECTORY", "/var/lib/akvorado-settings")) / "client-names.json"

    def client_names(self):
        if not self.names_file.exists():
            return {}
        return json.loads(self.names_file.read_text(encoding="utf-8"))

    def rename_client(self, body):
        ip = body.get("ip")
        name = body.get("name")
        try:
            if not isinstance(ip, str) or "%" in ip:
                raise ValueError
            address = ipaddress.ip_address(ip)
        except ValueError:
            raise RequestError(400, "Enter a valid client IP address.") from None
        if isinstance(address, ipaddress.IPv6Address):
            address = address.ipv4_mapped or address
        ip = str(address)
        if not isinstance(name, str):
            raise RequestError(400, "Enter a client name of up to 64 characters.")
        name = name.strip()
        if len(name) > 64 or (name and not name.isprintable()):
            raise RequestError(400, "Use up to 64 printable characters for the client name.")
        names = self.client_names()
        if name:
            names[ip] = name
        else:
            names.pop(ip, None)
        write_config(self.names_file, json.dumps(names, ensure_ascii=False, sort_keys=True) + "\n")
        return {"ip": ip, "name": name}

    def get(self):
        _, accounts = named_auth_block(self.args.caddyfile.read_text(encoding="utf-8"))
        return {
            "currentUser": self.args.admin,
            "users": [
                {"username": name, "role": "admin" if name == self.args.admin else "viewer"}
                for name in accounts
            ],
            "retention": self.retention(self.args.config.read_text(encoding="utf-8")),
        }


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(20)
        super().setup()

    def log_message(self, format, *args):
        # Do not log request headers, paths, or bodies.
        pass

    def response(self, status, value):
        payload = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def body(self):
        if self.headers.get_content_type() != "application/json":
            raise RequestError(415, "Use an application/json request.")
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, UnicodeError):
            raise RequestError(400, "Invalid settings request.") from None
        return body

    def dispatch(self):
        settings = self.server.settings
        try:
            identity = self.headers.get_all(AUTH_HEADER) or []
            admin = identity == [settings.args.admin]
            path = urlsplit(self.path).path
            read_names = self.command == "GET" and path == CLIENT_NAMES
            if not admin and (not read_names or len(identity) != 1 or not re.fullmatch(USER, identity[0])):
                raise RequestError(403, "Settings are only available to the administrator.")
            if self.command != "GET" and self.headers.get("Origin") not in (None, settings.args.origin):
                raise RequestError(403, "Settings changes must come from this site.")
            body = self.body() if self.command in ("POST", "PUT") else {}
            with settings.lock:
                if read_names:
                    result = {"names": settings.client_names(), "canEdit": admin}
                elif self.command == "PUT" and path == CLIENT_NAMES:
                    result = settings.rename_client(body)
                elif self.command == "GET" and path == ENDPOINT:
                    result = settings.get()
                elif self.command == "POST" and path == ENDPOINT + "/users":
                    result = settings.change_user(self.command, body.get("username"), body)
                elif self.command in ("PUT", "DELETE") and path.startswith(ENDPOINT + "/users/"):
                    username = unquote(path.removeprefix(ENDPOINT + "/users/"))
                    result = settings.change_user(self.command, username, body)
                elif self.command == "PUT" and path == ENDPOINT + "/retention":
                    result = settings.change_retention(body)
                else:
                    raise RequestError(404, "Settings endpoint not found.")
        except RequestError as err:
            self.response(err.status, {"message": str(err)})
        except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as err:
            logging.error("Settings request failed: %s", type(err).__name__)
            self.response(HTTPStatus.SERVICE_UNAVAILABLE, {"message": "Unable to read or apply settings."})
        else:
            self.response(HTTPStatus.OK, result)

    do_GET = do_POST = do_PUT = do_DELETE = dispatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--admin", required=True)
    parser.add_argument("--caddy", required=True)
    parser.add_argument("--clickhouse", required=True)
    parser.add_argument("--database", default="default")
    parser.add_argument("--caddyfile", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings(args)
    if args.admin not in named_auth_block(args.caddyfile.read_text(encoding="utf-8"))[1]:
        raise RuntimeError("The administrator account must already exist in Caddy")
    if args.socket.is_socket():
        args.socket.unlink()
    os.umask(0o177)
    logging.basicConfig(level=logging.INFO)
    with socketserver.ThreadingUnixStreamServer(str(args.socket), Handler) as server:
        os.chmod(args.socket, 0o600)
        server.settings = settings
        server.serve_forever()


if __name__ == "__main__":
    main()
