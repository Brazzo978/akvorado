<!-- SPDX-FileCopyrightText: 2026 Akvorado contributors -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="container mx-auto w-full space-y-5 px-4 py-6 sm:px-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Clients</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
          Internet traffic by client IP
        </p>
      </div>
      <InputButton v-if="!selected" type="alternative" @click="openWizard()"
        >Manage subnets</InputButton
      >
      <div v-else class="flex flex-wrap gap-2">
        <InputButton
          v-if="canEditClientNames"
          type="alternative"
          @click="openNameEditor"
        >
          {{
            clientNames[selected] ? "Edit friendly name" : "Add friendly name"
          }}
        </InputButton>
        <InputButton type="alternative" @click="closeDetail"
          >Back to rankings</InputButton
        >
      </div>
    </header>

    <dialog
      ref="wizard"
      class="m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border border-gray-200 bg-white p-6 text-gray-900 shadow-xl backdrop:bg-slate-950/55 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-100"
    >
      <form class="space-y-4" @submit.prevent="saveSubnets">
        <div>
          <h2 class="text-lg font-semibold">Add your subnets</h2>
          <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
            Enter one CIDR per line. Leave the list empty to show all observed
            client IPs.
          </p>
        </div>
        <label class="block text-sm font-medium">
          Subnets in CIDR notation
          <textarea
            v-model="draft"
            rows="4"
            spellcheck="false"
            placeholder="192.0.2.0/24"
            class="mt-1 w-full rounded-md border border-gray-300 bg-transparent p-2 font-mono text-sm dark:border-slate-600"
          />
        </label>
        <p
          v-if="wizardError"
          class="text-sm text-red-700 dark:text-red-400"
          role="alert"
        >
          {{ wizardError }}
        </p>
        <div class="flex flex-wrap justify-end gap-2">
          <InputButton type="alternative" class="px-4" @click="wizard?.close()"
            >Close</InputButton
          >
          <InputButton
            attr-type="submit"
            :loading="saving"
            :disabled="saving"
            class="px-4"
            >Save subnets</InputButton
          >
        </div>
      </form>
    </dialog>

    <dialog
      ref="nameDialog"
      aria-labelledby="client-name-title"
      class="m-auto w-[calc(100%-2rem)] max-w-md rounded-xl border border-gray-200 bg-white p-6 text-gray-900 shadow-xl backdrop:bg-slate-950/55 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-100"
    >
      <form class="space-y-4" @submit.prevent="saveClientName">
        <h2 id="client-name-title" class="text-lg font-semibold">
          Friendly name for {{ selected }}
        </h2>
        <label class="block text-sm font-medium">
          Friendly name
          <input
            v-model="nameDraft"
            maxlength="64"
            autofocus
            :disabled="nameSaving"
            class="mt-1 w-full rounded-md border border-gray-300 bg-transparent p-2 dark:border-slate-600"
          />
        </label>
        <p class="text-xs text-gray-600 dark:text-slate-400">
          Leave blank to remove the name.
        </p>
        <p
          v-if="nameError"
          role="alert"
          class="text-sm text-red-700 dark:text-red-400"
        >
          {{ nameError }}
        </p>
        <div class="flex justify-end gap-2">
          <InputButton
            type="alternative"
            :disabled="nameSaving"
            @click="nameDialog?.close()"
            >Cancel</InputButton
          >
          <InputButton
            attr-type="submit"
            :disabled="nameSaving"
            :loading="nameSaving"
            >Save name</InputButton
          >
        </div>
      </form>
    </dialog>

    <template v-if="!selected">
      <form
        class="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 p-4 dark:border-slate-700"
        @submit.prevent="refresh"
      >
        <label class="grid gap-1 text-sm font-medium">
          Time range
          <select
            v-model.number="hours"
            class="rounded-md border border-gray-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-800"
          >
            <option :value="0.25">Last 15 minutes</option>
            <option :value="1">Last hour</option>
            <option :value="6">Last 6 hours</option>
            <option :value="24">Last 24 hours</option>
            <template v-if="config?.clientHistory">
              <option :value="168">Last 7 days</option>
              <option :value="720">Last 30 days</option>
              <option :value="1440">Last 60 days</option>
            </template>
          </select>
        </label>
        <label class="grid gap-1 text-sm font-medium">
          Sort by
          <select
            v-model="sort"
            class="rounded-md border border-gray-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="total">Total traffic</option>
            <option value="download">Download</option>
            <option value="upload">Upload</option>
          </select>
        </label>
        <label class="grid grow gap-1 text-sm font-medium sm:grow-0">
          Find IP
          <input
            v-model.trim="search"
            spellcheck="false"
            placeholder="IP address"
            class="rounded-md border border-gray-300 bg-transparent px-3 py-2 font-normal dark:border-slate-600"
          />
        </label>
        <InputButton
          attr-type="submit"
          :loading="loading"
          :disabled="loading"
          class="px-4"
          >Refresh</InputButton
        >
        <div
          class="flex w-full flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-slate-400"
        >
          <span v-if="!prefixes.length">All observed client IPs</span>
          <span
            v-for="prefix in prefixes"
            :key="prefix"
            class="rounded-full bg-slate-100 px-2.5 py-1 font-mono dark:bg-slate-800"
            >{{ prefix }}</span
          >
        </div>
      </form>

      <InfoBox v-if="listError">{{ listError }}</InfoBox>
      <section
        class="overflow-hidden rounded-xl border border-gray-200 dark:border-slate-700"
      >
        <div
          class="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
        >
          <h2 class="font-semibold">IP rankings</h2>
          <p v-if="active" class="text-xs text-gray-600 dark:text-slate-400">
            {{ formatPeriod(active.start, active.end) }} · Estimated from
            sampled IPFIX
          </p>
        </div>
        <p
          v-if="active && coverage"
          class="px-4 pb-3 text-xs text-gray-600 dark:text-slate-400"
        >
          <template v-if="coverage.start && coverage.end">
            Hourly history available
            {{ formatPeriod(coverage.start, coverage.end) }}
          </template>
          <template v-else
            >Waiting for the first hour of client history.</template
          >
        </p>
        <div class="overflow-x-auto" :aria-busy="loading">
          <table class="w-full min-w-[34rem] text-left text-sm tabular-nums">
            <thead
              class="border-y border-gray-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800"
            >
              <tr>
                <th scope="col" class="px-4 py-2">Rank</th>
                <th scope="col" class="px-4 py-2">Client IP</th>
                <th
                  scope="col"
                  class="w-1/2 min-w-44 px-4 py-2"
                  title="Same scale for download and upload on this page"
                >
                  <div class="flex justify-between gap-3">
                    <span class="text-blue-700 dark:text-blue-300"
                      >Download</span
                    >
                    <span class="text-red-700 dark:text-red-300">Upload</span>
                  </div>
                </th>
                <th scope="col" class="px-4 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-slate-800">
              <tr
                v-for="(row, idx) in rows"
                :key="row.ip"
                class="hover:bg-slate-50 dark:hover:bg-slate-800/60"
              >
                <td class="px-4 py-2.5 text-gray-500">
                  {{ offset + idx + 1 }}
                </td>
                <th scope="row" class="px-4 py-2.5 font-medium">
                  <button
                    type="button"
                    class="cursor-pointer font-mono font-semibold text-blue-700 hover:underline dark:text-blue-300"
                    @click="openDetail(row.ip)"
                  >
                    {{ row.ip }}
                  </button>
                  <span
                    v-if="clientNames[row.ip]"
                    :title="clientNames[row.ip]"
                    class="ml-2 inline-block max-w-40 truncate align-bottom text-gray-700 dark:text-slate-200"
                    >{{ clientNames[row.ip] }}</span
                  >
                </th>
                <td class="px-4 py-2">
                  <div
                    class="mb-1 flex justify-between gap-3 whitespace-nowrap text-xs"
                  >
                    <span
                      ><span class="sr-only">Download </span
                      >{{ formatVolume(row.download) }}</span
                    >
                    <span
                      ><span class="sr-only">Upload </span
                      >{{ formatVolume(row.upload) }}</span
                    >
                  </div>
                  <div
                    aria-hidden="true"
                    class="relative grid h-2.5 grid-cols-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700"
                  >
                    <div class="flex justify-end">
                      <div
                        class="rounded-l-full bg-blue-600 dark:bg-blue-400"
                        :style="{ width: barWidth(row.download) }"
                      />
                    </div>
                    <div class="flex">
                      <div
                        class="rounded-r-full bg-red-600 dark:bg-red-400"
                        :style="{ width: barWidth(row.upload) }"
                      />
                    </div>
                    <div
                      class="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-slate-500 dark:bg-slate-300"
                    />
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right font-semibold">
                  {{ formatVolume(row.download + row.upload) }}
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td
                  colspan="4"
                  class="px-4 py-8 text-center text-gray-600 dark:text-slate-400"
                >
                  {{
                    loading
                      ? "Loading…"
                      : "No client traffic matches these filters."
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <footer
          v-if="offset || hasMore"
          class="flex justify-end gap-2 border-t border-gray-200 px-4 py-3 dark:border-slate-700"
        >
          <InputButton
            type="alternative"
            :disabled="loading || !offset"
            @click="loadPage(offset - 25)"
            >Previous</InputButton
          >
          <InputButton
            type="alternative"
            :disabled="loading || !hasMore"
            @click="loadPage(offset + 25)"
            >Next</InputButton
          >
        </footer>
      </section>
    </template>

    <section v-else aria-live="polite">
      <InfoBox v-if="detailError">{{ detailError }}</InfoBox>
      <p v-else-if="!detail" class="py-4 text-sm" role="status">
        Loading traffic for {{ selected }}…
      </p>
      <ClientTrafficDetail
        v-else-if="active"
        :ip="selected"
        :friendly-name="clientNames[selected]"
        :traffic="detail"
        :start="active.start"
        :end="active.end"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
import {
  computed,
  inject,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import InputButton from "@/components/InputButton.vue";
import InfoBox from "@/components/InfoBox.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";
import ClientTrafficDetail, {
  type ClientDetail,
  type HistoryCoverage,
  type TrafficVolume,
  formatPeriod,
  formatVolume,
} from "./ClientsPage/ClientTrafficDetail.vue";

type ClientRow = TrafficVolume & { ip: string };
type Ranking = "total" | "download" | "upload";
type TrafficRequest = {
  start: string;
  end: string;
  prefixes: string[];
  ip?: string;
  sort: Ranking;
  offset: number;
};

const config = inject(ServerConfigKey)!;
const storageKey = "akvorado-client-subnets";
const namesEndpoint = "api/v0/console/settings/client-names";
const clientNames = ref<Record<string, string>>({});
const canEditClientNames = ref(false);
const nameDialog = ref<HTMLDialogElement>();
const nameDraft = ref("");
const nameError = ref("");
const nameSaving = ref(false);
const namesRequest = new AbortController();

const wizard = ref<HTMLDialogElement>();
const draft = ref("");
const saving = ref(false);
const wizardError = ref("");
const prefixes = ref<string[]>([]);
const hours = ref(1);
const sort = ref<Ranking>("total");
const search = ref("");
const active = ref<TrafficRequest>();
const rows = ref<ClientRow[]>([]);
const coverage = ref<HistoryCoverage | null>(null);
const largestDirection = computed(() =>
  Math.max(
    1,
    ...rows.value.flatMap(({ download, upload }) => [download, upload]),
  ),
);
const barWidth = (bytes: number) =>
  (bytes / largestDirection.value) * 100 + "%";
const loading = ref(false);
const listError = ref("");
const offset = ref(0);
const hasMore = ref(false);
const selected = ref("");
const detail = ref<ClientDetail>();
const detailError = ref("");
let listRequest: AbortController | undefined;
let detailRequest: AbortController | undefined;

async function post<T>(
  action: "traffic" | "detail",
  body: TrafficRequest,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch("api/v0/console/clients/" + action, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (response.status === 400)
    throw new Error("Check the IP address and use CIDR notation for subnets.");
  if (!response.ok) throw new Error("Unable to load client traffic.");
  return response.json();
}

async function loadPage(next: number) {
  if (!active.value) return false;
  listRequest?.abort();
  const request = new AbortController();
  listRequest = request;
  loading.value = true;
  listError.value = "";
  try {
    const result = await post<{
      rows: ClientRow[];
      hasMore: boolean;
      coverage?: HistoryCoverage | null;
    }>("traffic", { ...active.value, offset: next }, request.signal);
    rows.value = result.rows;
    coverage.value = result.coverage ?? null;
    hasMore.value = result.hasMore;
    offset.value = next;
    return true;
  } catch (error) {
    if (!request.signal.aborted) listError.value = (error as Error).message;
    return false;
  } finally {
    if (listRequest === request) loading.value = false;
  }
}

function refresh() {
  const step = hours.value > 24 ? 3_600_000 : 60_000;
  const end = Math.floor(Date.now() / step) * step;
  active.value = {
    start: new Date(end - hours.value * 3_600_000).toISOString(),
    end: new Date(end).toISOString(),
    prefixes: prefixes.value,
    ip: search.value || undefined,
    sort: sort.value,
    offset: 0,
  };
  rows.value = [];
  coverage.value = null;
  offset.value = 0;
  hasMore.value = false;
  return loadPage(0);
}

function openWizard() {
  draft.value = prefixes.value.join("\n");
  wizardError.value = "";
  wizard.value?.showModal();
}

async function saveSubnets() {
  const next = [...new Set(draft.value.split(/[\s,]+/).filter(Boolean))];
  if (next.length > 16 || next.some((prefix) => !prefix.includes("/"))) {
    wizardError.value = "Enter up to 16 subnets in CIDR notation.";
    return;
  }
  const previous = prefixes.value;
  prefixes.value = next;
  saving.value = true;
  const loaded = await refresh();
  saving.value = false;
  if (!loaded) {
    wizardError.value = listError.value;
    prefixes.value = previous;
    await refresh();
    return;
  }
  localStorage.setItem(storageKey, next.join("\n"));
  wizard.value?.close();
}

async function loadClientNames() {
  try {
    const result = await fetch(namesEndpoint, { signal: namesRequest.signal });
    if (result.ok) {
      const data = await result.json();
      clientNames.value = data.names;
      canEditClientNames.value = data.canEdit;
    }
  } catch {
    // Client traffic is available independently of the optional names service.
  }
}

function openNameEditor() {
  if (nameSaving.value) return;
  nameDraft.value = clientNames.value[selected.value] ?? "";
  nameError.value = "";
  nameDialog.value?.showModal();
}

async function saveClientName() {
  if (!selected.value || nameSaving.value) return;
  nameSaving.value = true;
  nameError.value = "";
  try {
    const result = await fetch(namesEndpoint, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ip: selected.value,
        name: nameDraft.value.trim(),
      }),
    });
    if (!result.ok) {
      nameError.value = "Unable to save the name.";
      return;
    }
    const { ip, name } = await result.json();
    if (name) {
      clientNames.value[ip] = name;
    } else {
      delete clientNames.value[ip];
    }
    nameDialog.value?.close();
  } catch {
    nameError.value = "Unable to save the name.";
  } finally {
    nameSaving.value = false;
  }
}

async function openDetail(ip: string) {
  if (!active.value) return;
  detailRequest?.abort();
  const request = new AbortController();
  detailRequest = request;
  selected.value = ip;
  detail.value = undefined;
  detailError.value = "";
  try {
    detail.value = await post<ClientDetail>(
      "detail",
      { ...active.value, ip },
      request.signal,
    );
  } catch (error) {
    if (!request.signal.aborted) detailError.value = (error as Error).message;
  }
}

function closeDetail() {
  detailRequest?.abort();
  selected.value = "";
}

watch(
  config,
  (data) => {
    if (!data) return;
    const saved = localStorage.getItem(storageKey);
    prefixes.value =
      saved === null
        ? (data.clientSubnets ?? [])
        : saved.split("\n").filter(Boolean);
    void refresh();
    if (saved === null) void nextTick(openWizard);
  },
  { immediate: true },
);

onMounted(() => void loadClientNames());
onUnmounted(() => {
  namesRequest.abort();
  listRequest?.abort();
  detailRequest?.abort();
});
</script>
