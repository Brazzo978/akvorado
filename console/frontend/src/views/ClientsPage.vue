<!-- SPDX-FileCopyrightText: 2026 Akvorado contributors -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="container mx-auto w-full space-y-5 px-4 py-6 sm:px-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Clienti</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
          Traffico Internet per IP lato LAN
        </p>
      </div>
      <InputButton v-if="!selected" type="alternative" @click="openWizard()"
        >Gestisci subnet</InputButton
      >
      <InputButton v-else type="alternative" @click="closeDetail"
        >Torna alla classifica</InputButton
      >
    </header>

    <dialog
      ref="wizard"
      class="m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border border-gray-200 bg-white p-6 text-gray-900 shadow-xl backdrop:bg-slate-950/55 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-100"
    >
      <form class="space-y-4" @submit.prevent="saveSubnets">
        <div>
          <h2 class="text-lg font-semibold">Aggiungi le tue subnet</h2>
          <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
            Inserisci un CIDR per riga. Puoi lasciare il campo vuoto per vedere
            tutti gli IP lato LAN osservati.
          </p>
        </div>
        <label class="block text-sm font-medium">
          Subnet in formato CIDR
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
            >Chiudi</InputButton
          >
          <InputButton
            attr-type="submit"
            :loading="saving"
            :disabled="saving"
            class="px-4"
            >Salva subnet</InputButton
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
          Periodo
          <select
            v-model.number="hours"
            class="rounded-md border border-gray-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-800"
          >
            <option :value="0.25">Ultimi 15 minuti</option>
            <option :value="1">Ultima ora</option>
            <option :value="6">Ultime 6 ore</option>
            <option :value="24">Ultime 24 ore</option>
          </select>
        </label>
        <label class="grid gap-1 text-sm font-medium">
          Ordina per
          <select
            v-model="sort"
            class="rounded-md border border-gray-300 bg-white px-3 py-2 font-normal dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="total">Traffico totale</option>
            <option value="download">Download</option>
            <option value="upload">Upload</option>
          </select>
        </label>
        <label class="grid grow gap-1 text-sm font-medium sm:grow-0">
          Cerca IP
          <input
            v-model.trim="search"
            spellcheck="false"
            placeholder="Indirizzo IP"
            class="rounded-md border border-gray-300 bg-transparent px-3 py-2 font-normal dark:border-slate-600"
          />
        </label>
        <InputButton
          attr-type="submit"
          :loading="loading"
          :disabled="loading"
          class="px-4"
          >Aggiorna</InputButton
        >
        <div
          class="flex w-full flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-slate-400"
        >
          <span v-if="!prefixes.length">Tutti gli IP lato LAN osservati</span>
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
          <h2 class="font-semibold">Classifica IP</h2>
          <p v-if="active" class="text-xs text-gray-600 dark:text-slate-400">
            {{ formatPeriod(active.start, active.end) }} · Volumi stimati da
            IPFIX
          </p>
        </div>
        <div class="overflow-x-auto" :aria-busy="loading">
          <table class="w-full min-w-[34rem] text-left text-sm tabular-nums">
            <thead
              class="border-y border-gray-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800"
            >
              <tr>
                <th scope="col" class="px-4 py-2">Pos.</th>
                <th scope="col" class="px-4 py-2">Client IP</th>
                <th scope="col" class="px-4 py-2 text-right">Download</th>
                <th scope="col" class="px-4 py-2 text-right">Upload</th>
                <th scope="col" class="px-4 py-2 text-right">Totale</th>
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
                </th>
                <td class="px-4 py-2.5 text-right">
                  {{ formatVolume(row.download) }}
                </td>
                <td class="px-4 py-2.5 text-right">
                  {{ formatVolume(row.upload) }}
                </td>
                <td class="px-4 py-2.5 text-right font-semibold">
                  {{ formatVolume(row.download + row.upload) }}
                </td>
              </tr>
              <tr v-if="!rows.length">
                <td
                  colspan="5"
                  class="px-4 py-8 text-center text-gray-600 dark:text-slate-400"
                >
                  {{
                    loading
                      ? "Caricamento…"
                      : "Nessun IP con traffico per i filtri selezionati."
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
            >Indietro</InputButton
          >
          <InputButton
            type="alternative"
            :disabled="loading || !hasMore"
            @click="loadPage(offset + 25)"
            >Avanti</InputButton
          >
        </footer>
      </section>
    </template>

    <section v-else aria-live="polite">
      <InfoBox v-if="detailError">{{ detailError }}</InfoBox>
      <p v-else-if="!detail" class="py-4 text-sm" role="status">
        Caricamento del traffico di {{ selected }}…
      </p>
      <ClientTrafficDetail
        v-else-if="active"
        :ip="selected"
        :traffic="detail"
        :start="active.start"
        :end="active.end"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
import { inject, nextTick, onUnmounted, ref, watch } from "vue";
import InputButton from "@/components/InputButton.vue";
import InfoBox from "@/components/InfoBox.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";
import ClientTrafficDetail, {
  type ClientDetail,
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
  if (response.status === 400) throw new Error((await response.json()).message);
  if (!response.ok)
    throw new Error("Impossibile caricare i dati sul traffico.");
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
    const result = await post<{ rows: ClientRow[]; hasMore: boolean }>(
      "traffic",
      { ...active.value, offset: next },
      request.signal,
    );
    rows.value = result.rows;
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
  const end = Math.floor(Date.now() / 60_000) * 60_000;
  active.value = {
    start: new Date(end - hours.value * 3_600_000).toISOString(),
    end: new Date(end).toISOString(),
    prefixes: prefixes.value,
    ip: search.value || undefined,
    sort: sort.value,
    offset: 0,
  };
  rows.value = [];
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
    wizardError.value = "Inserisci fino a 16 subnet in formato CIDR.";
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

onUnmounted(() => {
  listRequest?.abort();
  detailRequest?.abort();
});
</script>
