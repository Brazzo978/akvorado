# SPDX-FileCopyrightText: 2026 Akvorado contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Refresh hourly client traffic from raw Akvorado flows."""

import argparse
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import re
import subprocess

HISTORY = "flows_clients_hourly"
STAGE = HISTORY + "_stage"
SCHEMA = """
(
    Hour DateTime('UTC'),
    ClientIP IPv6,
    Proto UInt32,
    RemoteAS UInt32,
    Download UInt64,
    Upload UInt64
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(Hour)
ORDER BY (Hour, ClientIP, Proto, RemoteAS)
TTL Hour + toIntervalDay(60)
"""


def query(args, sql):
    return subprocess.run(
        ["docker", "exec", args.container, "clickhouse-client", "--database", args.database, "--query", sql],
        check=True, text=True, stdout=subprocess.PIPE, timeout=180,
    ).stdout.strip()


def refresh(args, start, end):
    partition = start.strftime("%Y%m%d")
    query(args, f"TRUNCATE TABLE {STAGE}")
    query(args, f"""
        INSERT INTO {STAGE}
        WITH InIfBoundary = 'internal' AS outbound,
             if(outbound, SrcAddr, DstAddr) AS client_ip,
             toUInt64(Bytes) * toUInt64(SamplingRate) AS weighted_bytes
        SELECT toStartOfHour(toTimeZone(TimeReceived, 'UTC')) AS hour_bucket, client_ip, Proto,
               if(outbound, DstAS, SrcAS) AS remote_as,
               sumIf(weighted_bytes, NOT outbound), sumIf(weighted_bytes, outbound)
        FROM flows
        WHERE TimeReceived >= toDateTime({int(start.timestamp())}, 'UTC')
          AND TimeReceived < toDateTime({int(end.timestamp())}, 'UTC')
          AND InIfName != '' AND OutIfName != ''
          AND ((outbound AND OutIfBoundary = 'external')
               OR (InIfBoundary = 'external' AND OutIfBoundary = 'internal'))
        GROUP BY hour_bucket, client_ip, Proto, remote_as
        SETTINGS max_threads=2, max_execution_time=150, max_memory_usage=1500000000
    """)
    if query(args, f"SELECT count() != 0 FROM {STAGE}") == "1":
        query(args, f"ALTER TABLE {HISTORY} REPLACE PARTITION {int(partition)} FROM {STAGE}")
        logging.info("Refreshed client history for UTC day %s", partition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--database", default="default")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.database):
        parser.error("invalid database name")

    logging.basicConfig(level=logging.INFO)
    query(args, f"CREATE TABLE IF NOT EXISTS {HISTORY} {SCHEMA}")
    query(args, f"CREATE TABLE IF NOT EXISTS {STAGE} {SCHEMA}")
    now = datetime.now(timezone.utc)
    cutoff = now.replace(minute=0, second=0, microsecond=0)
    today = cutoff.replace(hour=0)
    state = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/akvorado-clients-history")) / "cutoff"
    last_refresh = None
    if state.exists():
        last_refresh = datetime.fromtimestamp(int(state.read_text()), timezone.utc)
    raw_start = int(query(args, """
        SELECT toUnixTimestamp(min(min_time)) FROM system.parts
        WHERE active AND database=currentDatabase() AND table='flows'
    """) or 0)
    if not raw_start:
        logging.info("Waiting for raw client traffic")
        return

    existing = set(query(args, f"SELECT DISTINCT partition FROM system.parts WHERE active AND database=currentDatabase() AND table='{HISTORY}'").splitlines())
    earliest = datetime.fromtimestamp(raw_start, timezone.utc)
    backfill_start = max(earliest.replace(hour=0, minute=0, second=0, microsecond=0), today - timedelta(days=60))
    # Refresh the previous UTC day to pick up delayed flows. After an outage,
    # repeat the days since the last complete refresh while raw data still exists.
    repair_from = (last_refresh or backfill_start).replace(hour=0) - timedelta(days=1)
    start = backfill_start
    while start < cutoff:
        end = min(start + timedelta(days=1), cutoff)
        missing = start.strftime("%Y%m%d") not in existing
        recent = start == today or (start >= repair_from and earliest <= start)
        if missing or recent:
            refresh(args, start, end)
        start += timedelta(days=1)
    query(args, f"TRUNCATE TABLE {STAGE}")
    pending = state.with_suffix(".pending")
    pending.write_text(str(int(cutoff.timestamp())))
    pending.replace(state)


if __name__ == "__main__":
    main()
