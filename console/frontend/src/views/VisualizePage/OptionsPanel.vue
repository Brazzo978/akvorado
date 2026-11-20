<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <aside
    class="max-w-full shrink-0 overflow-y-auto border-b border-gray-200 bg-gray-50 dark:border-slate-700 dark:bg-slate-800 lg:border-r lg:border-b-0"
    :class="
      open ? 'max-h-[55dvh] w-full lg:max-h-none lg:w-80' : 'w-full lg:w-16'
    "
  >
    <div
      class="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-gray-200 bg-gray-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-800"
    >
      <h2 v-if="open" class="text-base font-semibold">Chart setup</h2>
      <button
        type="button"
        class="rounded px-2 py-1 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:text-blue-300 dark:hover:bg-slate-700"
        :aria-expanded="open"
        aria-controls="chart-setup"
        @click="open = !open"
      >
        {{ open ? "Hide" : "Setup" }}
      </button>
    </div>
    <form
      v-show="open"
      id="chart-setup"
      class="grid gap-4 p-4"
      autocomplete="off"
      spellcheck="false"
      @submit.prevent="submitOptions()"
    >
      <InputButton
        attr-type="submit"
        :disabled="hasErrors && !loading"
        :loading="loading"
        :type="loading ? 'alternative' : 'primary'"
        class="w-full justify-center"
        >{{ loading ? "Cancel" : applyLabel }}</InputButton
      >

      <section class="grid gap-2">
        <SectionLabel>
          <template #default>
            <span class="flex items-center gap-1">
              Time period
              <button
                type="button"
                title="Zoom out"
                :disabled="timeRange?.errors"
                class="cursor-pointer text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-gray-400 dark:hover:text-gray-200 dark:disabled:hover:text-gray-400"
                @click="timeRangeInput?.zoomOut()"
              >
                <ZoomOutIcon class="h-4 w-4" aria-hidden="true" />
              </button>
            </span>
          </template>
          <template #hint>
            <label
              class="flex items-center gap-1"
              :class="liveRange ? 'cursor-pointer' : 'cursor-not-allowed'"
              :title="autoRefreshHint"
            >
              <span>Auto refresh</span>
              <select
                v-model="autoRefresh"
                :disabled="!liveRange"
                class="cursor-pointer rounded border border-gray-300 bg-white px-1 py-0.5 text-xs text-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-400"
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
          </template>
        </SectionLabel>
        <InputTimeRange
          ref="timeRangeInput"
          v-model="timeRange"
          @submit="submitOptions(true)"
        />
      </section>

      <section class="grid gap-2">
        <label class="grid gap-1.5 text-sm font-semibold">
          Measure
          <select
            v-model="units"
            class="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm font-normal dark:border-slate-600 dark:bg-slate-900"
          >
            <option value="l3bps">IP traffic (bits/s)</option>
            <option value="l2bps">Ethernet traffic (bits/s)</option>
            <option value="inl2%">Inbound link utilization (%)</option>
            <option value="outl2%">Outbound link utilization (%)</option>
            <option value="pps">Packets per second</option>
            <option value="fps">Flows per second</option>
          </select>
        </label>
        <InputCheckbox
          v-if="bidirectionalGraphTypes.includes(graphType.type)"
          v-model="bidirectional"
          label="Show both directions"
        />
      </section>

      <section class="grid gap-2">
        <SectionLabel>
          <span class="flex items-center gap-1">
            Group traffic by
            <button
              type="button"
              title="Reverse direction"
              :disabled="!!dimensions?.errors"
              class="cursor-pointer text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-gray-400 dark:hover:text-gray-200 dark:disabled:hover:text-gray-400"
              @click="reverseDimensions()"
            >
              <SwitchHorizontalIcon class="h-4 w-4" aria-hidden="true" />
            </button>
          </span>
        </SectionLabel>
        <InputDimensions
          v-model="dimensions"
          :min-dimensions="graphType.name === graphTypes.sankey ? 2 : 0"
          @submit="submitOptions()"
        />
      </section>

      <details
        class="rounded-md border border-gray-200 px-3 py-2 dark:border-slate-700"
      >
        <summary class="cursor-pointer text-sm font-semibold">
          Advanced options
          <span
            v-if="filter?.errors"
            class="ml-1 text-xs font-normal text-red-700 dark:text-red-400"
            >Filter error</span
          >
          <span
            v-else-if="filter?.expression.trim()"
            class="ml-1 text-xs font-normal text-gray-600 dark:text-gray-400"
            >Filter active</span
          >
        </summary>
        <div class="mt-3 grid gap-3">
          <InputListBox
            v-model="graphType"
            :items="graphTypeList"
            label="Graph type"
          >
            <template #selected>{{ graphType.name }}</template>
            <template #item="{ name }">
              <div class="flex w-full items-center justify-between">
                <span>{{ name }}</span>
                <GraphIcon
                  :name="name"
                  class="mr-1 inline h-4 text-gray-500 dark:text-gray-400"
                />
              </div>
            </template>
          </InputListBox>
          <InputCheckbox
            v-if="previousPeriodGraphTypes.includes(graphType.type)"
            v-model="previousPeriod"
            label="Compare with previous period"
          />
          <SectionLabel>
            <template #default>
              <span class="flex items-center gap-1">
                Filter
                <button
                  type="button"
                  title="Reverse direction"
                  :disabled="!!filter?.errors"
                  class="cursor-pointer text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-gray-400 dark:hover:text-gray-200 dark:disabled:hover:text-gray-400"
                  @click="reverseFilter()"
                >
                  <SwitchHorizontalIcon class="h-4 w-4" aria-hidden="true" />
                </button>
              </span>
            </template>
            <template #hint>
              <kbd
                class="rounded border border-gray-300 bg-gray-200 px-1 dark:border-gray-600 dark:bg-gray-900"
                >Ctrl-Enter</kbd
              >
              to execute
            </template>
          </SectionLabel>
          <InputFilter v-model="filter" @submit="submitOptions()" />
        </div>
      </details>
    </form>
  </aside>
</template>

<script lang="ts" setup>
import { ref, watch, computed, inject, toRaw } from "vue";
import { useIntervalFn } from "@vueuse/core";
import { Date as SugarDate } from "sugar-date";
import { SwitchHorizontalIcon, ZoomOutIcon } from "@heroicons/vue/solid";
import {
  default as InputTimeRange,
  type ModelType as InputTimeRangeModelType,
} from "@/components/InputTimeRange.vue";
import {
  default as InputDimensions,
  type ModelType as InputDimensionsModelType,
} from "@/components/InputDimensions.vue";
import InputListBox from "@/components/InputListBox.vue";
import InputButton from "@/components/InputButton.vue";
import InputCheckbox from "@/components/InputCheckbox.vue";
import {
  default as InputFilter,
  type ModelType as InputFilterModelType,
} from "@/components/InputFilter.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";
import SectionLabel from "./SectionLabel.vue";
import GraphIcon from "./GraphIcon.vue";
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

const open = ref(true);
const graphType = ref(graphTypeList[0]);
const timeRange = ref<InputTimeRangeModelType>(null);
const timeRangeInput = ref<InstanceType<typeof InputTimeRange>>();
const dimensions = ref<InputDimensionsModelType>(null);
const filter = ref<InputFilterModelType>(null);
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
    ? "Refresh"
    : "Apply",
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
