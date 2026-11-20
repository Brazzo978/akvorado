<!-- SPDX-FileCopyrightText: 2022 Free Mobile -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <nav
    aria-label="Main navigation"
    class="z-40 w-full border-b border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"
  >
    <div
      class="container mx-auto flex flex-wrap items-center justify-between gap-x-4 px-4 sm:flex-nowrap sm:px-6"
    >
      <router-link to="/" class="flex items-center gap-2 py-2.5 font-semibold">
        <img src="@/assets/images/akvorado.svg" class="h-8" alt="" />
        <span>Akvorado</span>
      </router-link>
      <ul class="order-last flex w-full gap-1 sm:order-none sm:w-auto">
        <li v-for="item in navigation" :key="item.link">
          <router-link
            :to="item.link"
            :aria-current="item.current ? 'page' : undefined"
            class="block rounded-t-md border-b-2 px-3 py-2.5 text-sm font-medium"
            :class="
              item.current
                ? 'border-blue-600 bg-blue-50 text-blue-800 dark:border-blue-400 dark:bg-slate-800 dark:text-blue-300'
                : 'border-transparent text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            "
          >
            {{ item.name }}
          </router-link>
        </li>
      </ul>
      <div class="flex items-center gap-1">
        <DarkModeSwitcher />
        <UserMenu />
      </div>
    </div>
  </nav>
</template>

<script lang="ts" setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import DarkModeSwitcher from "@/components/DarkModeSwitcher.vue";
import UserMenu from "@/components/UserMenu.vue";

const route = useRoute();
const navigation = computed(() => [
  { name: "Home", link: "/", current: route.path === "/" },
  { name: "Clienti", link: "/clients", current: route.path === "/clients" },
  {
    name: "Visualize",
    link: "/visualize",
    current: route.path.startsWith("/visualize"),
  },
]);
</script>
