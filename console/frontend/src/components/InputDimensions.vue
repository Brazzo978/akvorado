<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<!--
 Default, 4 columns:
 - Dimensions list box (4 columns)
 - IPv4 /x (optional), IPv6 /x (optional), Limit, Top by
 Large (lg:), 2 columns:
 - Dimensions list box (2 columns)
 - IPv4 /x (optional), IPv6 /x (optional)
 - Limit, Top By
-->

<template>
  <div
    class="grid grid-cols-4 gap-2 lg:grid-cols-2"
    @keydown.capture="handleKeydown"
  >
    <InputListBox
      v-model="selectedDimensions"
      :items="dimensions"
      :error="dimensionsError"
      multiple
      label="Choose fields"
      filter="keywords"
      class="col-span-full"
    >
      <template #selected>
        <span v-if="selectedDimensions.length === 0">All traffic</span>
        <draggable
          v-model="selectedDimensions"
          class="block flex flex-wrap gap-1"
          tag="span"
          item-key="id"
        >
          <template #item="{ element: dimension }">
            <span
              class="flex cursor-grab items-center gap-1 rounded border-2 bg-violet-100 px-1.5 dark:bg-slate-800 dark:text-gray-200"
              :style="{ borderColor: dimension.color }"
            >
              <span class="leading-4">{{ dimension.label }}</span>
              <button
                type="button"
                class="cursor-pointer rounded hover:text-blue-700 dark:hover:text-white"
                :aria-label="'Remove ' + dimension.label"
                @click.stop="removeDimension(dimension)"
              >
                <XIcon class="h-4 w-4" aria-hidden="true" />
              </button>
            </span>
          </template>
        </draggable>
      </template>
      <template #item="{ label, color }">
        <span :style="{ backgroundColor: color }" class="inline w-1 rounded"
          >&nbsp;</span
        >
        {{ label }}
      </template>
    </InputListBox>
    <InputString
      v-if="canAggregate"
      v-model="truncate4"
      class="grow"
      label="IPv4 prefix"
      :error="truncate4Error"
    />
    <InputString
      v-if="canAggregate"
      v-model="truncate6"
      class="grow"
      label="IPv6 prefix"
      :error="truncate6Error"
    />
    <InputString
      v-model="limit"
      class="grow"
      label="Top results"
      :error="limitError"
    />
    <InputListBox
      v-model="limitType"
      :items="computationModeList"
      class="grow"
      label="Rank by"
    >
      <template #selected>{{ limitType.name }}</template>
      <template #item="{ name }">
        <div class="flex w-full items-center justify-between">
          <span>{{ name }}</span>
        </div>
      </template>
    </InputListBox>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, computed, inject } from "vue";
import draggable from "vuedraggable";
import { XIcon } from "@heroicons/vue/solid";
import { dataColor } from "@/utils";
import InputString from "@/components/InputString.vue";
import InputListBox from "@/components/InputListBox.vue";
import { ServerConfigKey } from "@/components/ServerConfigProvider.vue";
import { isEqual, intersection } from "lodash-es";

const props = withDefaults(
  defineProps<{
    modelValue: ModelType;
    minDimensions?: number;
  }>(),
  {
    minDimensions: 0,
  },
);
const emit = defineEmits<{
  "update:modelValue": [value: typeof props.modelValue];
  submit: [];
}>();

const serverConfiguration = inject(ServerConfigKey)!;
const selectedDimensions = ref<Array<(typeof dimensions.value)[0]>>([]);
const dimensionsError = computed(() => {
  if (selectedDimensions.value.length < props.minDimensions) {
    return "At least two dimensions are required";
  }
  return "";
});
const limit = ref("10");
const limitError = computed(() => {
  const val = parseInt(limit.value);
  if (isNaN(val)) {
    return "Not a number";
  }
  if (val < 1) {
    return "Should be ≥ 1";
  }
  const upperLimit = serverConfiguration.value?.dimensionsLimit ?? 50;
  if (val > upperLimit) {
    return `Should be ≤ ${upperLimit}`;
  }
  return "";
});

const computationModes = {
  avg: "Average",
  max: "Peak",
  last: "Latest",
} as const;

const computationModeList = Object.entries(computationModes).map(
  ([k, v], idx) => ({
    id: idx + 1,
    type: k as keyof typeof computationModes, // why isn't it infered?
    name: v,
  }),
);
const limitType = ref(computationModeList[0]);

const canAggregate = computed(
  () =>
    intersection(
      selectedDimensions.value.map((dim) => dim.name),
      serverConfiguration.value?.truncatable || [],
    ).length > 0,
);
const truncate4 = ref("32");
const truncate4Error = computed(() => {
  const val = parseInt(truncate4.value);
  if (isNaN(val) || val <= 0 || val > 32) {
    return "0 < x ≤ 32";
  }
  return "";
});
const truncate6 = ref("128");
const truncate6Error = computed(() => {
  const val = parseInt(truncate6.value);
  if (isNaN(val) || val <= 0 || val > 128) {
    return "0 < x ≤ 128";
  }
  return "";
});
const hasErrors = computed(
  () =>
    !!limitError.value ||
    !!dimensionsError.value ||
    !!truncate4Error.value ||
    !!truncate6Error.value,
);

const directionLabels: Record<string, string> = {
  Src: "Source",
  Dst: "Destination",
  InIf: "Ingress",
  OutIf: "Egress",
};
const fieldLabels: Record<string, string> = {
  Addr: "IP address",
  AS: "network (AS)",
  NetPrefix: "network prefix",
  Name: "interface name",
  Description: "interface description",
  Speed: "interface speed",
  Provider: "interface provider",
  Connectivity: "interface connectivity",
  Boundary: "interface boundary",
  EType: "IP version",
  Proto: "protocol",
};
const dimensions = computed(() =>
  (serverConfiguration.value?.dimensions ?? []).map((name, idx) => {
    const prefix = /^(Src|Dst|InIf|OutIf)/.exec(name)?.[0] ?? "";
    const field = name.slice(prefix.length);
    const fieldLabel =
      fieldLabels[field] ?? field.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
    const label = prefix
      ? directionLabels[prefix] + " " + fieldLabel
      : fieldLabel;
    return {
      id: idx + 1,
      name,
      label,
      keywords: name + " " + label,
      color: dataColor(
        ["Exporter", "Src", "Dst", "In", "Out", ""].findIndex((p) =>
          name.startsWith(p),
        ),
      ),
    };
  }),
);

const removeDimension = (dimension: (typeof dimensions.value)[0]) => {
  selectedDimensions.value = selectedDimensions.value.filter(
    (d) => d !== dimension,
  );
};

const handleKeydown = (event: KeyboardEvent) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    if (!hasErrors.value) {
      emit("submit");
    }
  }
};

watch(
  () => [props.modelValue, dimensions.value] as const,
  ([value, dimensions]) => {
    if (value) {
      limit.value = value.limit.toString();
      limitType.value =
        computationModeList.find((mode) => mode.type === value.limitType) ||
        computationModeList[0];
      truncate4.value = value.truncate4.toString();
      truncate6.value = value.truncate6.toString();
    }
    if (value)
      selectedDimensions.value = value.selected
        .map((name) => dimensions.find((d) => d.name === name))
        .filter((d): d is (typeof dimensions)[0] => !!d);
  },
  { immediate: true, deep: true },
);
watch(
  [
    selectedDimensions,
    limit,
    limitType,
    truncate4,
    truncate6,
    hasErrors,
  ] as const,
  ([selected, limit, limitType, truncate4, truncate6, hasErrors]) => {
    const updated = {
      selected: selected.map((d) => d.name),
      limit: parseInt(limit),
      limitType: limitType.type,
      truncate4: parseInt(truncate4),
      truncate6: parseInt(truncate6),
      errors: hasErrors,
    };
    if (
      !isEqual(updated, props.modelValue) &&
      !isNaN(updated.limit) &&
      !isNaN(updated.truncate4) &&
      !isNaN(updated.truncate6)
    ) {
      emit("update:modelValue", updated);
    }
  },
);
</script>

<script lang="ts">
export type ModelType = {
  selected: string[];
  limit: number;
  limitType: string;
  truncate4: number;
  truncate6: number;
  errors?: boolean;
} | null;
</script>
