<!-- SPDX-FileCopyrightText: 2026 Akvorado contributors -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="space-y-4">
    <header>
      <h2 class="font-mono text-xl font-semibold">{{ ip }}</h2>
      <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
        {{ formatPeriod(start, end) }} · Stima IPFIX
      </p>
    </header>
    <p
      v-if="!traffic.points.length"
      class="rounded-xl border border-gray-200 p-5 dark:border-slate-700"
    >
      Nessun flusso nel periodo.
    </p>
    <template v-else>
      <dl class="grid grid-cols-2 gap-3 md:grid-cols-5">
        <div
          v-for="item in stats"
          :key="item.label"
          class="rounded-xl border border-gray-200 px-3 py-3 dark:border-slate-700"
        >
          <dt class="text-xs text-gray-600 dark:text-slate-400">
            {{ item.label }}
          </dt>
          <dd class="mt-1 text-lg font-semibold tabular-nums">
            {{ item.value }}
          </dd>
        </div>
      </dl>

      <section
        class="rounded-xl border border-gray-200 p-4 dark:border-slate-700"
      >
        <h3 class="font-semibold">Velocità nel tempo</h3>
        <p class="text-xs text-gray-600 dark:text-slate-400">
          Banda media per minuto
        </p>
        <div class="h-80">
          <v-chart
            :option="chart"
            :theme="isDark ? 'dark' : undefined"
            autoresize
          />
        </div>
      </section>

      <div class="grid gap-4 xl:grid-cols-2">
        <section
          v-for="group in breakdowns"
          :key="group.label"
          class="min-w-0 rounded-xl border border-gray-200 p-4 dark:border-slate-700"
        >
          <h3 class="font-semibold">{{ group.label }}</h3>
          <div class="mt-2 overflow-x-auto">
            <table class="w-full min-w-[22rem] text-left text-sm tabular-nums">
              <thead
                class="border-b border-gray-200 text-xs text-gray-600 dark:border-slate-700 dark:text-slate-400"
              >
                <tr>
                  <th scope="col" class="px-2 py-2">{{ group.name }}</th>
                  <th scope="col" class="px-2 py-2 text-right">Download</th>
                  <th scope="col" class="px-2 py-2 text-right">Upload</th>
                  <th scope="col" class="px-2 py-2 text-right">Totale</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-slate-800">
                <tr v-for="row in group.rows" :key="row.id">
                  <th scope="row" class="px-2 py-2 font-medium">
                    {{
                      row.name ||
                      (group.name === "AS remoto"
                        ? "AS sconosciuto"
                        : "Protocollo " + row.id)
                    }}
                    <span
                      v-if="group.name === 'AS remoto' && row.id"
                      class="block font-mono text-xs text-gray-600 dark:text-slate-400"
                      >AS{{ row.id }}</span
                    >
                  </th>
                  <td class="px-2 py-2 text-right">
                    {{ formatVolume(row.download) }}
                  </td>
                  <td class="px-2 py-2 text-right">
                    {{ formatVolume(row.upload) }}
                  </td>
                  <td class="px-2 py-2 text-right font-semibold">
                    {{ formatVolume(row.download + row.upload) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script lang="ts">
import { formatXps } from "@/utils";

export type TrafficVolume = { download: number; upload: number };
type TrafficPoint = TrafficVolume & { time: number };
type TrafficBreakdown = TrafficVolume & { id: number; name: string };
export type ClientDetail = {
  total: TrafficVolume;
  peakDownloadBps: number;
  peakUploadBps: number;
  points: TrafficPoint[];
  protocols: TrafficBreakdown[];
  networks: TrafficBreakdown[];
};
const dateFormat = new Intl.DateTimeFormat("it-IT", {
  dateStyle: "short",
  timeStyle: "short",
});
export function formatPeriod(start: string, end: string) {
  return dateFormat.formatRange(new Date(start), new Date(end));
}
export function formatVolume(bytes: number) {
  return bytes === 0 ? "0 B" : formatXps(bytes) + "B";
}
</script>

<script lang="ts" setup>
import { computed, inject } from "vue";
import { use, type ComposeOption } from "echarts/core";
import { LineChart, type LineSeriesOption } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  type DataZoomComponentOption,
  type GridComponentOption,
  type LegendComponentOption,
  type TooltipComponentOption,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import VChart from "vue-echarts";
import { ThemeKey } from "@/components/ThemeProvider.vue";

use([
  CanvasRenderer,
  LineChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);
type ChartOption = ComposeOption<
  | LineSeriesOption
  | DataZoomComponentOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>;
const { isDark } = inject(ThemeKey)!;
const props = defineProps<{
  ip: string;
  start: string;
  end: string;
  traffic: ClientDetail;
}>();
const formatSpeed = (bps: number) =>
  bps === 0 ? "0 bps" : formatXps(bps) + "bps";

const stats = computed(() => [
  { label: "Download", value: formatVolume(props.traffic.total.download) },
  { label: "Upload", value: formatVolume(props.traffic.total.upload) },
  {
    label: "Totale",
    value: formatVolume(
      props.traffic.total.download + props.traffic.total.upload,
    ),
  },
  {
    label: "Picco download (1 min)",
    value: formatSpeed(props.traffic.peakDownloadBps),
  },
  {
    label: "Picco upload (1 min)",
    value: formatSpeed(props.traffic.peakUploadBps),
  },
]);
const breakdowns = computed(() => [
  {
    label: "Traffico per protocollo",
    name: "Protocollo",
    rows: props.traffic.protocols,
  },
  { label: "Top reti remote", name: "AS remoto", rows: props.traffic.networks },
]);
const chart = computed((): ChartOption => {
  const start = Date.parse(props.start);
  const end = Date.parse(props.end);
  const points = new Map(
    props.traffic.points.map((point) => [point.time * 1000, point]),
  );
  const times = Array.from(
    { length: (end - start) / 60_000 },
    (_, idx) => start + idx * 60_000,
  );
  return {
    backgroundColor: "transparent",
    legend: { top: 0 },
    grid: { left: 8, right: 20, top: 35, bottom: 64 },
    xAxis: { type: "time" },
    yAxis: { type: "value", axisLabel: { formatter: formatSpeed } },
    tooltip: {
      trigger: "axis",
      confine: true,
      valueFormatter: (value) => formatSpeed(Number(value ?? 0)),
    },
    dataZoom: [
      { type: "inside", zoomOnMouseWheel: "ctrl" },
      { type: "slider", height: 22, bottom: 5 },
    ],
    series: (["download", "upload"] as const).map((key) => ({
      name: key === "download" ? "Download" : "Upload",
      type: "line",
      showSymbol: false,
      areaStyle: { opacity: 0.12 },
      data: times.map((time) => [
        time,
        ((points.get(time)?.[key] ?? 0) * 8) / 60,
      ]),
    })),
  };
});
</script>
