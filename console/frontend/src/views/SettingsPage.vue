<!-- SPDX-FileCopyrightText: 2026 Akvorado contributors -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <div class="container mx-auto w-full space-y-5 px-4 py-6 sm:px-6">
    <h1 class="text-2xl font-semibold tracking-tight">Settings</h1>
    <p
      v-if="loading"
      class="text-sm text-slate-600 dark:text-slate-400"
      role="status"
    >
      Loading settings…
    </p>
    <div
      v-if="error"
      role="alert"
      class="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200"
    >
      {{ error }}
      <button
        v-if="!settings"
        type="button"
        class="ml-2 cursor-pointer font-semibold underline"
        @click="loadSettings"
      >
        Retry
      </button>
    </div>
    <p
      v-if="notice"
      role="status"
      class="rounded-lg bg-green-50 p-3 text-sm text-green-800 dark:bg-green-950 dark:text-green-200"
    >
      {{ notice }}
    </p>

    <template v-if="settings">
      <section
        class="rounded-xl border border-slate-200 p-4 dark:border-slate-700 sm:p-5"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold">Users</h2>
            <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Signed in as {{ settings.currentUser }}
            </p>
          </div>
          <InputButton
            type="alternative"
            :disabled="busy"
            @click="toggleAddUser"
            >{{ showAddUser ? "Cancel" : "Add user" }}</InputButton
          >
        </div>

        <form
          v-if="showAddUser"
          class="mt-4 grid gap-3 rounded-lg bg-slate-50 p-4 dark:bg-slate-800 sm:grid-cols-2"
          @submit.prevent="addUser"
        >
          <label class="grid gap-1 text-sm font-medium">
            Username
            <input
              v-model.trim="newUsername"
              required
              autocomplete="off"
              spellcheck="false"
              :disabled="busy"
              :class="inputClass"
            />
          </label>
          <label class="grid gap-1 text-sm font-medium">
            Password
            <input
              v-model="newPassword"
              required
              type="password"
              autocomplete="new-password"
              :disabled="busy"
              :class="inputClass"
            />
          </label>
          <div
            class="flex flex-wrap items-center justify-between gap-3 sm:col-span-2"
          >
            <p class="text-sm text-slate-600 dark:text-slate-400">
              New users have viewer access.
            </p>
            <InputButton
              attr-type="submit"
              :disabled="busy || !newUsername || !newPassword"
              :loading="busy"
              >Add user</InputButton
            >
          </div>
        </form>

        <div class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[30rem] text-left text-sm">
            <thead
              class="border-b border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-400"
            >
              <tr>
                <th scope="col" class="px-2 py-2 font-medium">Username</th>
                <th scope="col" class="px-2 py-2 font-medium">Role</th>
                <th scope="col" class="px-2 py-2 text-right font-medium">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
              <template v-for="user in settings.users" :key="user.username">
                <tr>
                  <th scope="row" class="px-2 py-3 font-medium">
                    {{ user.username }}
                    <span
                      v-if="user.username === settings.currentUser"
                      class="ml-1 text-xs font-normal text-slate-500"
                      >(you)</span
                    >
                  </th>
                  <td class="px-2 py-3 capitalize">{{ user.role }}</td>
                  <td class="px-2 py-3">
                    <div class="flex flex-wrap justify-end gap-2">
                      <InputButton
                        type="alternative"
                        size="small"
                        :disabled="busy"
                        :aria-label="'Change password for ' + user.username"
                        @click="openPassword(user.username)"
                        >Change password</InputButton
                      >
                      <InputButton
                        v-if="
                          user.role !== 'admin' &&
                          user.username !== settings.currentUser
                        "
                        type="alternative"
                        size="small"
                        :disabled="busy"
                        :aria-label="'Remove user ' + user.username"
                        @click="removeUser(user.username)"
                        >Remove</InputButton
                      >
                    </div>
                  </td>
                </tr>
                <tr v-if="passwordUser === user.username">
                  <td colspan="3" class="px-2 pb-3">
                    <form
                      class="flex flex-wrap items-end gap-2 rounded-lg bg-slate-50 p-3 dark:bg-slate-800"
                      @submit.prevent="changePassword"
                    >
                      <label
                        class="grid min-w-48 flex-1 gap-1 text-sm font-medium"
                      >
                        New password for {{ user.username }}
                        <input
                          v-model="passwordValue"
                          required
                          type="password"
                          autocomplete="new-password"
                          :disabled="busy"
                          :class="inputClass"
                        />
                      </label>
                      <InputButton
                        attr-type="submit"
                        :disabled="busy || !passwordValue"
                        :loading="busy"
                        >Save password</InputButton
                      >
                      <InputButton
                        type="alternative"
                        :disabled="busy"
                        @click="closePassword"
                        >Cancel</InputButton
                      >
                    </form>
                  </td>
                </tr>
              </template>
              <tr v-if="settings.users.length === 0">
                <td
                  colspan="3"
                  class="px-2 py-4 text-slate-600 dark:text-slate-400"
                >
                  No users found.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section
        class="rounded-xl border border-slate-200 p-4 dark:border-slate-700 sm:p-5"
      >
        <h2 class="text-lg font-semibold">Data retention</h2>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Choose how long to keep each type of traffic data.
        </p>
        <div class="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
          <form
            v-for="item in settings.retention"
            :key="item.table"
            class="flex flex-wrap items-end justify-between gap-3 py-3 first:pt-0 last:pb-0"
            @submit.prevent="saveRetention(item)"
          >
            <div>
              <h3 class="font-medium">{{ item.label }}</h3>
              <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
                Current retention
                {{ item.days === null ? "Unlimited" : item.days + " days" }}
              </p>
            </div>
            <div v-if="item.editable" class="flex flex-wrap items-end gap-2">
              <label class="grid gap-1 text-sm font-medium">
                Days
                <input
                  v-model="retentionDraft[item.table]"
                  type="number"
                  min="1"
                  step="1"
                  inputmode="numeric"
                  :aria-label="'Retention days for ' + item.label"
                  :disabled="busy"
                  class="w-28 rounded-md border border-slate-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-900"
                />
              </label>
              <InputButton
                attr-type="submit"
                :disabled="busy || !canSaveRetention(item)"
                >Save</InputButton
              >
            </div>
          </form>
          <p
            v-if="settings.retention.length === 0"
            class="py-3 text-sm text-slate-600 dark:text-slate-400"
          >
            No retention settings available.
          </p>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from "vue";
import InputButton from "@/components/InputButton.vue";

type User = { username: string; role: "admin" | "viewer" };
type Retention = {
  table: string;
  label: string;
  days: number | null;
  editable: boolean;
};
type Settings = { currentUser: string; users: User[]; retention: Retention[] };

const settings = ref<Settings>();
const retentionDraft = ref<Record<string, string>>({});
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const showAddUser = ref(false);
const newUsername = ref("");
const newPassword = ref("");
const passwordUser = ref("");
const passwordValue = ref("");
const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-900";

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("api/v0/console/settings" + path, {
    method,
    cache: "no-store",
    ...(body === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
  });
  if (!response.ok) {
    let message = "";
    try {
      message = (await response.json()).message ?? "";
    } catch {
      // Some errors contain no JSON body.
    }
    throw new Error(message || "Request failed (" + response.status + ").");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

async function refresh() {
  const data = await request<Settings>("");
  settings.value = data;
  retentionDraft.value = Object.fromEntries(
    data.retention.map((item) => [
      item.table,
      item.days === null ? "" : String(item.days),
    ]),
  );
}

async function loadSettings() {
  loading.value = true;
  error.value = "";
  try {
    await refresh();
  } catch (cause) {
    error.value = (cause as Error).message || "Unable to load settings.";
  } finally {
    loading.value = false;
  }
}

async function mutate(
  path: string,
  method: string,
  body: unknown,
  success: string,
) {
  if (busy.value) return false;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await request(path, method, body);
    notice.value = success;
    try {
      await refresh();
    } catch {
      settings.value = undefined;
      error.value = "Changes were saved, but settings could not be reloaded.";
    }
    return true;
  } catch (cause) {
    error.value = (cause as Error).message || "Unable to save changes.";
    return false;
  } finally {
    busy.value = false;
  }
}

function toggleAddUser() {
  showAddUser.value = !showAddUser.value;
  newUsername.value = "";
  newPassword.value = "";
}

async function addUser() {
  if (!newUsername.value || !newPassword.value) return;
  const saved = await mutate(
    "/users",
    "POST",
    { username: newUsername.value, password: newPassword.value },
    "User added.",
  );
  newPassword.value = "";
  if (saved) {
    newUsername.value = "";
    showAddUser.value = false;
  }
}

function closePassword() {
  passwordUser.value = "";
  passwordValue.value = "";
}

function openPassword(username: string) {
  passwordValue.value = "";
  passwordUser.value = username;
}

async function changePassword() {
  if (!passwordUser.value || !passwordValue.value) return;
  const saved = await mutate(
    "/users/" + encodeURIComponent(passwordUser.value),
    "PUT",
    { password: passwordValue.value },
    "Password updated.",
  );
  passwordValue.value = "";
  if (saved) closePassword();
}

async function removeUser(username: string) {
  if (!window.confirm('Remove user "' + username + '"?')) return;
  await mutate(
    "/users/" + encodeURIComponent(username),
    "DELETE",
    undefined,
    "User removed.",
  );
}

function canSaveRetention(item: Retention) {
  const raw = retentionDraft.value[item.table] ?? "";
  const days = Number(raw);
  return (
    raw.trim() !== "" &&
    Number.isSafeInteger(days) &&
    days > 0 &&
    days !== item.days
  );
}

async function saveRetention(item: Retention) {
  if (!canSaveRetention(item)) return;
  const days = Number(retentionDraft.value[item.table]);
  const isReduction = item.days === null || days < item.days;
  if (
    isReduction &&
    !window.confirm(
      "Reduce " +
        item.label +
        " retention to " +
        days +
        " days? Older data may be removed.",
    )
  )
    return;
  await mutate(
    "/retention",
    "PUT",
    {
      table: item.table,
      days,
      expectedDays: item.days,
      confirmReduction: isReduction,
    },
    "Retention updated.",
  );
}

onMounted(loadSettings);
</script>
