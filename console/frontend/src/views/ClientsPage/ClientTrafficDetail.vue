<!-- SPDX-FileCopyrightText: 2026 Akvorado contributors -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="space-y-4">
    <header>
      <h2 class="flex flex-wrap items-baseline gap-x-3 text-xl font-semibold">
        <span class="font-mono">{{ ip }}</span>
        <span
          v-if="friendlyName"
          class="break-all text-gray-700 dark:text-slate-200"
          >{{ friendlyName }}</span
        >
      </h2>
      <p class="mt-1 text-sm text-gray-600 dark:text-slate-400">
        {{ formatPeriod(start, end) }} · Estimated from sampled IPFIX
      </p>
    </header>
    <p
      v-if="!traffic.points.length"
      class="rounded-xl border border-gray-200 p-5 dark:border-slate-700"
    >
      No flows in this time range.
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
        <h3 class="font-semibold">Traffic over time</h3>
        <p class="text-xs text-gray-600 dark:text-slate-400">
          {{ resolutionLabel }} average throughput
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
                  <th scope="col" class="px-2 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-slate-800">
                <tr v-for="row in group.rows" :key="row.id">
                  <th scope="row" class="px-2 py-2 font-medium">
                    {{
                      row.name ||
                      (group.name === "Remote AS"
                        ? "Unknown AS"
                        : "Protocol " + row.id)
                    }}
                    <span
                      v-if="group.name === 'Remote AS' && row.id"
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
export type HistoryCoverage = { start: string | null; end: string | null };
type TrafficPoint = TrafficVolume & { time: number };
type TrafficBreakdown = TrafficVolume & { id: number; name: string };
export type ClientDetail = {
  total: TrafficVolume;
  peakDownloadBps: number;
  peakUploadBps: number;
  bucketSeconds?: number;
  coverage?: HistoryCoverage | null;
  points: TrafficPoint[];
  protocols: TrafficBreakdown[];
  networks: TrafficBreakdown[];
};
const dateFormat = new Intl.DateTimeFormat("en-GB", {
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
  friendlyName?: string;
  start: string;
  end: string;
  traffic: ClientDetail;
}>();
const formatSpeed = (bps: number) =>
  bps === 0 ? "0 bps" : formatXps(bps) + "bps";

const bucketSeconds = computed(() => props.traffic.bucketSeconds ?? 60);
const resolutionLabel = computed(() =>
  bucketSeconds.value === 3600 ? "1-hour" : "1-minute",
);

const stats = computed(() => [
  { label: "Download", value: formatVolume(props.traffic.total.download) },
  { label: "Upload", value: formatVolume(props.traffic.total.upload) },
  {
    label: "Total",
    value: formatVolume(
      props.traffic.total.download + props.traffic.total.upload,
    ),
  },
  {
    label: `Peak download (${resolutionLabel.value} avg)`,
    value: formatSpeed(props.traffic.peakDownloadBps),
  },
  {
    label: `Peak upload (${resolutionLabel.value} avg)`,
    value: formatSpeed(props.traffic.peakUploadBps),
  },
]);
const breakdowns = computed(() => [
  {
    label: "Traffic by protocol",
    name: "Protocol",
    rows: props.traffic.protocols,
  },
  {
    label: "Top remote networks",
    name: "Remote AS",
    rows: props.traffic.networks,
  },
]);
const chart = computed((): ChartOption => {
  const coverage = props.traffic.coverage;
  const start = Math.max(
    Date.parse(props.start),
    coverage?.start ? Date.parse(coverage.start) : -Infinity,
  );
  const end = Math.min(
    Date.parse(props.end),
    coverage?.end ? Date.parse(coverage.end) : Infinity,
  );
  const step = bucketSeconds.value * 1000;
  const points = new Map(
    props.traffic.points.map((point) => [point.time * 1000, point]),
  );
  const times = Array.from(
    { length: Math.max(0, (end - start) / step) },
    (_, idx) => start + idx * step,
  );
  return {
    backgroundColor: "transparent",
    color: isDark.value ? ["#60a5fa", "#f87171"] : ["#2563eb", "#dc2626"],
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
        ((points.get(time)?.[key] ?? 0) * 8) / bucketSeconds.value,
      ]),
    })),
  };
});
</script>
