<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="container mx-auto space-y-5 px-4 py-6 sm:px-6">
    <header class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold tracking-tight">Traffic overview</h1>
      <div class="grid w-full grid-cols-2 gap-3 sm:w-auto">
        <WidgetFlowRate
          :refresh="refreshOften"
          class="rounded-xl border border-gray-200 px-4 py-2 text-center dark:border-slate-700"
        />
        <WidgetExporters
          :refresh="refreshOccasionally"
          class="rounded-xl border border-gray-200 px-4 py-2 text-center dark:border-slate-700"
        />
      </div>
    </header>

    <section
      class="min-w-0 rounded-xl border border-gray-200 p-4 dark:border-slate-700 sm:p-6"
    >
      <h2 class="text-lg font-semibold">Traffic over time</h2>
      <WidgetGraph :refresh="refreshInfrequently" />
    </section>

    <div class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <WidgetTop
        v-for="widget in topWidgets"
        :key="widget"
        :what="widget"
        :title="widgetTitle(widget)"
        :refresh="refreshOccasionally"
        class="min-w-0 rounded-xl border border-gray-200 p-4 dark:border-slate-700"
      />
    </div>

    <details
      class="rounded-xl border border-gray-200 p-4 dark:border-slate-700"
    >
      <summary class="cursor-pointer font-semibold">Raw flow details</summary>
      <WidgetLastFlow :refresh="refreshOften" class="mt-4 overflow-x-auto" />
    </details>
  </div>
</template>

<script lang="ts" setup>
import { inject, computed } from "vue";
import { useInterval } from "@vueuse/core";
import WidgetLastFlow from "./HomePage/WidgetLastFlow.vue";
import WidgetFlowRate from "./HomePage/WidgetFlowRate.vue";
import WidgetExporters from "./HomePage/WidgetExporters.vue";
import WidgetTop from "./HomePage/WidgetTop.vue";
import WidgetGraph from "./HomePage/WidgetGraph.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";

const serverConfiguration = inject(ServerConfigKey)!;
const topWidgets = computed(
  () => serverConfiguration.value?.homepageTopWidgets ?? [],
);
const widgetTitle = (name: string) =>
  ({
    "src-as": "Top source AS",
    "dst-as": "Top destination AS",
    "src-country": "Top source countries",
    "dst-country": "Top destination countries",
    exporter: "Top exporters",
    protocol: "Top protocols",
    etype: "IPv4/IPv6",
    "src-port": "Top source ports",
    "dst-port": "Top destination ports",
  })[name] ?? "???";

const refreshOften = useInterval(10_000);
const refreshOccasionally = useInterval(60_000);
const refreshInfrequently = useInterval(600_000);
</script>
