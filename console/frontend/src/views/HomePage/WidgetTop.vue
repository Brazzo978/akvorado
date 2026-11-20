<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div>
    <h2 class="font-semibold leading-relaxed">{{ title }}</h2>
    <div class="h-[280px]">
      <v-chart
        :option="options"
        :update-options="{ notMerge: true }"
        :theme="isDark ? 'dark' : undefined"
        autoresize
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, inject } from "vue";
import { useFetch } from "@vueuse/core";
import { ThemeKey } from "@/components/ThemeProvider.vue";
import { use, type ComposeOption } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  BarChart,
  PieChart,
  type BarSeriesOption,
  type PieSeriesOption,
} from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  type GridComponentOption,
  type TooltipComponentOption,
  type LegendComponentOption,
} from "echarts/components";
import VChart from "vue-echarts";
import { dataColor, dataColorGrey } from "../../utils";
const { isDark } = inject(ThemeKey)!;

const props = defineProps<{
  refresh: number;
  what: string;
  title: string;
}>();

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

type ECOption = ComposeOption<
  | BarSeriesOption
  | PieSeriesOption
  | TooltipComponentOption
  | LegendComponentOption
  | GridComponentOption
>;

const url = computed(
  () => `api/v0/console/widget/top/${props.what}?${props.refresh}`,
);
const { data } = useFetch(url, { refetch: true })
  .get()
  .json<
    { top: Array<{ name: string; percent: number }> } | { message: string }
  >();
const ranking = computed(() => {
  if (!data.value || "message" in data.value) return [];

  const entries = data.value.top;
  if (entries.length === 0) return [];
  const others = Math.max(
    100 - entries.reduce((sum, { percent }) => sum + percent, 0),
    0,
  );
  return [
    ...entries.map(({ name, percent }) => ({ name, value: percent })),
    { name: "Others", value: others },
  ].filter(({ value }) => value > 0.05);
});
const formatPercent = (value: number) => value.toFixed(2) + "%";

const options = computed((): ECOption => {
  const theme = isDark.value ? "dark" : "light";
  const entries = ranking.value.map((entry, index) => ({
    ...entry,
    itemStyle: {
      color:
        entry.name === "Others"
          ? dataColorGrey(0, false, theme)
          : dataColor(index, false, theme),
    },
  }));
  const common: ECOption = {
    darkMode: isDark.value,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      confine: true,
      valueFormatter: (value) => formatPercent(Number(value ?? 0)),
    },
  };

  if (props.what === "etype") {
    return {
      ...common,
      legend: { bottom: 4 },
      series: [
        {
          type: "pie",
          center: ["50%", "44%"],
          radius: ["43%", "70%"],
          label: { show: false },
          data: entries,
        },
      ],
    };
  }

  return {
    ...common,
    grid: { left: 0, right: 16, top: 12, bottom: 4 },
    xAxis: {
      type: "value",
      axisLabel: { formatter: "{value}%" },
      splitLine: { lineStyle: { opacity: 0.18 } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: entries.map(({ name }) => name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { width: 115, overflow: "truncate", interval: 0 },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 20,
        itemStyle: { borderRadius: [0, 5, 5, 0] },
        data: entries,
      },
    ],
  };
});
</script>
