<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <aside
    class="flex max-w-full shrink-0 flex-col border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800 lg:border-r lg:border-b-0"
    :class="
      open ? 'max-h-[58dvh] w-full lg:max-h-none lg:w-80' : 'w-full lg:w-20'
    "
  >
    <div
      class="flex items-center justify-between gap-2 border-b border-slate-200 px-3 py-2 dark:border-slate-700"
    >
      <h2 v-if="open" class="text-base font-semibold">Chart options</h2>
      <button
        type="button"
        class="cursor-pointer rounded px-2 py-1 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:text-blue-300 dark:hover:bg-slate-700"
        :aria-expanded="open"
        aria-controls="chart-setup"
        @click="open = !open"
      >
        {{ open ? "Hide" : "Options" }}
      </button>
    </div>

    <form
      v-show="open"
      id="chart-setup"
      class="flex min-h-0 flex-col"
      autocomplete="off"
      spellcheck="false"
      @submit.prevent="submitOptions()"
    >
      <div
        class="grid min-h-0 gap-4 overflow-y-auto px-4 py-3 [scrollbar-gutter:stable]"
      >
        <InputTimeRange
          ref="timeRangeInput"
          v-model="timeRange"
          @submit="submitOptions(true)"
        />

        <label class="grid gap-1 text-sm font-semibold">
          Metric
          <select v-model="units" :class="selectClass">
            <option value="l3bps">IP traffic (bits/s)</option>
            <option value="l2bps">Ethernet traffic (bits/s)</option>
            <option value="inl2%">Inbound link utilization (%)</option>
            <option value="outl2%">Outbound link utilization (%)</option>
            <option value="pps">Packets per second</option>
            <option value="fps">Flows per second</option>
          </select>
        </label>

        <section class="grid gap-1">
          <div class="flex flex-wrap items-center justify-between gap-1">
            <h3 class="text-sm font-semibold">Group by</h3>
            <button
              type="button"
              :disabled="!dimensions?.selected.length || !!dimensions.errors"
              class="cursor-pointer rounded px-1 text-xs font-medium text-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-blue-300"
              @click="reverseDimensions()"
            >
              Swap directions
            </button>
          </div>
          <InputDimensions
            v-model="dimensions"
            :min-dimensions="graphType.type === 'sankey' ? 2 : 0"
            @submit="submitOptions()"
          />
        </section>

        <section class="grid gap-2">
          <label class="grid gap-1 text-sm font-semibold">
            Chart type
            <select v-model="graphType" :class="selectClass">
              <option
                v-for="choice in graphTypeList"
                :key="choice.id"
                :value="choice"
              >
                {{ choice.name }}
              </option>
            </select>
          </label>
          <InputCheckbox
            v-if="bidirectionalGraphTypes.includes(graphType.type)"
            v-model="bidirectional"
            label="Show both traffic directions"
          />
        </section>

        <div class="grid gap-2">
          <details
            class="rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700"
          >
            <summary class="cursor-pointer text-sm font-medium">
              Filters
              <span
                class="ml-1 text-xs font-normal"
                :class="
                  filter?.errors
                    ? 'text-red-700 dark:text-red-300'
                    : 'text-slate-600 dark:text-slate-400'
                "
                >{{ filterSummary }}</span
              >
            </summary>
            <div class="mt-3 grid gap-2">
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="preset in filterPresets"
                  :key="preset.expression"
                  type="button"
                  :aria-pressed="
                    filter?.expression.trim() === preset.expression
                  "
                  class="cursor-pointer rounded border border-slate-300 px-2 py-1 text-xs aria-pressed:border-blue-500 aria-pressed:bg-blue-100 dark:border-slate-600 dark:aria-pressed:bg-blue-950"
                  @click="filter = { expression: preset.expression }"
                >
                  {{ preset.label }}
                </button>
              </div>
              <InputFilter v-model="filter" @submit="submitOptions()" />
              <button
                type="button"
                :disabled="!filter?.expression.trim() || !!filter.errors"
                class="justify-self-start rounded px-1 text-xs font-medium text-blue-700 enabled:cursor-pointer disabled:opacity-50 dark:text-blue-300"
                @click="reverseFilter()"
              >
                Swap filter directions
              </button>
            </div>
          </details>

          <details
            class="rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700"
          >
            <summary class="cursor-pointer text-sm font-medium">
              Time tools
              <span
                v-if="autoRefresh"
                class="ml-1 text-xs text-slate-600 dark:text-slate-400"
                >Auto refresh on</span
              >
            </summary>
            <div class="mt-2 grid gap-2">
              <label
                class="grid gap-1 text-sm font-medium"
                :title="autoRefreshHint"
              >
                Auto refresh
                <select
                  v-model="autoRefresh"
                  :disabled="!liveRange"
                  :class="selectClass"
                >
                  <option
                    v-for="interval in refreshIntervals"
                    :key="interval.value"
                    :value="interval.value"
                  >
                    {{ interval.label }}
                  </option>
                </select>
              </label>
              <InputCheckbox
                v-if="previousPeriodGraphTypes.includes(graphType.type)"
                v-model="previousPeriod"
                label="Compare with previous period"
              />
              <button
                type="button"
                :disabled="!timeRange || timeRange.errors"
                class="justify-self-start rounded px-1 text-xs font-medium text-blue-700 enabled:cursor-pointer disabled:opacity-50 dark:text-blue-300"
                @click="timeRangeInput?.zoomOut()"
              >
                Widen time range
              </button>
            </div>
          </details>
        </div>
      </div>

      <div
        class="shrink-0 border-t border-slate-200 px-4 py-3 dark:border-slate-700"
      >
        <InputButton
          attr-type="submit"
          :disabled="hasErrors && !loading"
          :loading="loading"
          :type="loading ? 'alternative' : 'primary'"
          class="w-full justify-center"
          >{{ loading ? "Cancel query" : applyLabel }}</InputButton
        >
      </div>
    </form>
  </aside>
</template>

<script lang="ts" setup>
import { ref, watch, computed, inject, toRaw } from "vue";
import { useIntervalFn } from "@vueuse/core";
import { Date as SugarDate } from "sugar-date";
import {
  default as InputTimeRange,
  type ModelType as InputTimeRangeModelType,
} from "@/components/InputTimeRange.vue";
import {
  default as InputDimensions,
  type ModelType as InputDimensionsModelType,
} from "@/components/InputDimensions.vue";
import InputButton from "@/components/InputButton.vue";
import InputCheckbox from "@/components/InputCheckbox.vue";
import {
  default as InputFilter,
  type ModelType as InputFilterModelType,
} from "@/components/InputFilter.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";
import type { Units } from ".";
import { isEqual, omit } from "lodash-es";

const props = withDefaults(
  defineProps<{
    modelValue: ModelType;
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);
const emit = defineEmits<{
  "update:modelValue": [value: typeof props.modelValue, auto?: boolean];
  cancel: [];
}>();

const graphTypeList = Object.entries(graphTypes).map(([k, v], idx) => ({
  id: idx + 1,
  type: k as keyof typeof graphTypes, // why isn't it infered?
  name: v,
}));

const bidirectionalGraphTypes: (keyof typeof graphTypes)[] = [
  "stacked",
  "stacked100",
  "lines",
  "grid",
  "sankey",
];

const previousPeriodGraphTypes: (keyof typeof graphTypes)[] = ["stacked"];

const selectClass =
  "w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm font-normal disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900";

const filterPresets = [
  { label: "All traffic", expression: "" },
  { label: "External ingress", expression: "InIfBoundary = external" },
  { label: "External egress", expression: "OutIfBoundary = external" },
];

const open = ref(true);
const graphType = ref(graphTypeList[0]);
const timeRange = ref<InputTimeRangeModelType>(null);
const timeRangeInput = ref<InstanceType<typeof InputTimeRange>>();
const dimensions = ref<InputDimensionsModelType>(null);
const filter = ref<InputFilterModelType>(null);
const filterSummary = computed(() => {
  if (filter.value?.errors) return "Check filter";
  const expression = filter.value?.expression.trim() ?? "";
  return (
    filterPresets.find((preset) => preset.expression === expression)?.label ??
    "Custom filter"
  );
});
const units = ref<Units>("l3bps");
const bidirectional = ref(false);
const previousPeriod = ref(false);

const submitOptions = (force?: boolean, auto?: boolean) => {
  if (!force && props.loading) {
    emit("cancel");
  } else {
    if (options.value !== null && !hasErrors.value) {
      emit(
        "update:modelValue",
        {
          ...options.value,
          start: SugarDate.create(options.value.humanStart).toISOString(),
          end: SugarDate.create(options.value.humanEnd).toISOString(),
        },
        auto,
      );
    }
  }
};

const reverse = async (input: {
  dimensions?: string[];
  filter?: string;
}): Promise<{ dimensions: string[]; filter: string } | null> => {
  const response = await fetch("api/v0/console/graph/reverse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) return null;
  return response.json();
};
const reverseDimensions = async () => {
  if (!dimensions.value) return;
  const data = await reverse({ dimensions: dimensions.value.selected });
  if (!data || !dimensions.value) return;
  dimensions.value = { ...dimensions.value, selected: data.dimensions };
};
const reverseFilter = async () => {
  if (!filter.value) return;
  const data = await reverse({ filter: filter.value.expression });
  if (!data) return;
  filter.value = { expression: data.filter };
};

// Querying again only brings new data when the range follows the clock, so
// this is limited to a range ending with "now".
const refreshIntervals = [
  { value: 0, label: "off" },
  { value: 5_000, label: "5s" },
  { value: 10_000, label: "10s" },
  { value: 30_000, label: "30s" },
  { value: 60_000, label: "1m" },
  { value: 300_000, label: "5m" },
];
const autoRefresh = ref(0);
const liveRange = computed(
  () => timeRange.value?.end.trim().toLowerCase() === "now",
);
const autoRefreshHint = computed(() =>
  liveRange.value
    ? "Query again at a regular interval"
    : 'Only available when the range ends with "now"',
);
watch(liveRange, (live) => {
  if (!live) autoRefresh.value = 0;
});
const { pause, resume } = useIntervalFn(
  () => {
    // Skip the tick while a query runs: a query slower than the interval would
    // keep cancelling and restarting itself.
    if (!props.loading) submitOptions(true, true);
  },
  () => autoRefresh.value || 60_000,
  { immediate: false },
);
watch(autoRefresh, (interval) => (interval ? resume() : pause()));

const options = computed((): InternalModelType => {
  if (!timeRange.value || !dimensions.value || !filter.value) {
    return options.value;
  }
  return {
    graphType: graphType.value.type,
    humanStart: timeRange.value?.start,
    humanEnd: timeRange.value?.end,
    dimensions: dimensions.value?.selected,
    limit: dimensions.value?.limit,
    limitType: dimensions.value?.limitType,
    "truncate-v4": dimensions.value?.truncate4,
    "truncate-v6": dimensions.value?.truncate6,
    filter: filter.value?.expression,
    units: units.value,
    bidirectional:
      bidirectionalGraphTypes.includes(graphType.value.type) &&
      bidirectional.value,
    previousPeriod:
      previousPeriodGraphTypes.includes(graphType.value.type) &&
      previousPeriod.value,
  };
});
const applyLabel = computed(() =>
  isEqual(options.value, omit(props.modelValue, ["start", "end"]))
    ? "Refresh chart"
    : "Run query",
);
const hasErrors = computed(
  () =>
    !!(
      timeRange.value?.errors ||
      dimensions.value?.errors ||
      filter.value?.errors
    ),
);

const serverConfiguration = inject(ServerConfigKey)!;
watch(
  () =>
    [
      props.modelValue,
      serverConfiguration.value?.defaultVisualizeOptions,
    ] as const,
  ([modelValue, defaultOptions]) => {
    if (!defaultOptions) return;
    const currentValue: NonNullable<InternalModelType> = modelValue ?? {
      graphType: defaultOptions.graphType,
      humanStart: defaultOptions.start,
      humanEnd: defaultOptions.end,
      dimensions: toRaw(defaultOptions.dimensions),
      limit: defaultOptions.limit,
      limitType: defaultOptions.limitType,
      "truncate-v4": 32,
      "truncate-v6": 128,
      filter: defaultOptions.filter,
      units: "l3bps",
      bidirectional: defaultOptions.bidirectional,
      previousPeriod: defaultOptions.previousPeriod,
    };

    // Dispatch values in refs
    const t = currentValue.graphType;
    graphType.value =
      graphTypeList.find(({ type }) => type === t) || graphTypeList[0];
    timeRange.value = {
      start: currentValue.humanStart,
      end: currentValue.humanEnd,
    };
    dimensions.value = {
      selected: [...currentValue.dimensions],
      limit: currentValue.limit,
      limitType: currentValue.limitType,
      truncate4: currentValue["truncate-v4"] || 32,
      truncate6: currentValue["truncate-v6"] || 128,
    };
    filter.value = { expression: currentValue.filter };
    units.value = currentValue.units;
    bidirectional.value = currentValue.bidirectional;
    previousPeriod.value = currentValue.previousPeriod;

    // A bit risky, but it seems to work.
    if (
      modelValue === null ||
      !modelValue.start ||
      !modelValue.end ||
      !isEqual(omit(modelValue, ["start", "end"]), options.value)
    ) {
      open.value = true;
      submitOptions(true);
    }
  },
  { immediate: true, deep: true },
);
</script>

<script lang="ts">
import { graphTypes } from "./graphtypes";

export type ModelType = {
  graphType: keyof typeof graphTypes;
  start: string;
  end: string;
  humanStart: string;
  humanEnd: string;
  dimensions: string[];
  limit: number;
  limitType: string;
  "truncate-v4": number;
  "truncate-v6": number;
  filter: string;
  units: Units;
  bidirectional: boolean;
  previousPeriod: boolean;
} | null;
type InternalModelType = Omit<NonNullable<ModelType>, "start" | "end"> | null;
</script>
