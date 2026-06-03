<template>
  <div class="app-layout" :class="{ 'dark-mode': store.theme === 'dark' }">
    <!-- Left Column Wrapper -->
    <div
      class="panel-wrapper left-wrapper"
      :class="{ 'is-expanded': store.hasSessions }"
    >
      <div class="panel-inner left-inner">
        <SearchStackPanel />
      </div>
    </div>

    <!-- Center Column Wrapper -->
    <div
      class="panel-wrapper center-wrapper"
      :class="{ 'is-expanded': store.hasSelectedTeachers }"
    >
      <div class="panel-inner center-inner">
        <InfoDisplayPanel />
      </div>
    </div>

    <!-- Right Column -->
    <div class="right-panel">
      <SearchBarPanel />
    </div>

    <!-- Theme Toggle -->
    <el-button
      class="theme-toggle"
      circle
      size="small"
      :type="store.theme === 'dark' ? 'primary' : 'default'"
      @click="store.toggleTheme()"
    >
      <el-icon>
        <Moon v-if="store.theme === 'light'" />
        <Sunny v-else />
      </el-icon>
    </el-button>
  </div>
</template>

<script setup>
import { watch, onMounted } from "vue";
import { useSearchStore } from "./stores/search.js";
import SearchStackPanel from "./components/SearchStackPanel.vue";
import InfoDisplayPanel from "./components/InfoDisplayPanel.vue";
import SearchBarPanel from "./components/SearchBarPanel.vue";
import { Moon, Sunny } from "@element-plus/icons-vue";

const store = useSearchStore();

function syncThemeClass() {
  const html = document.documentElement;
  if (store.theme === "dark") {
    html.classList.add("dark");
  } else {
    html.classList.remove("dark");
  }
}

onMounted(syncThemeClass);
watch(() => store.theme, syncThemeClass);
</script>

<style>
/* CSS Variables for theming */
:root {
  --app-bg: #f0f2f5;
  --panel-bg: #ffffff;
  --panel-border: #e4e7ed;
  --text-primary: #303133;
  --text-secondary: #606266;
  --text-muted: #909399;
  --accent-color: #409eff;
  --card-bg: #ffffff;
  --card-hover: #f5f7fa;
  --scrollbar-thumb: #dcdfe6;
  --scrollbar-track: transparent;
  --shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  --empty-color: #c0c4cc;
}

.dark-mode {
  --app-bg: #141414;
  --panel-bg: #1d1d1d;
  --panel-border: #2c2c2c;
  --text-primary: #e0e0e0;
  --text-secondary: #b0b0b0;
  --text-muted: #808080;
  --accent-color: #409eff;
  --card-bg: #1d1d1d;
  --card-hover: #2a2a2a;
  --scrollbar-thumb: #4a4a4a;
  --scrollbar-track: transparent;
  --shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.3);
  --empty-color: #606266;
}

/* Global overrides */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  background-color: var(--app-bg);
  color: var(--text-primary);
}

html.dark body {
  background-color: var(--app-bg);
}

/* Layout */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--app-bg);
  position: relative;
}

/* Drawer wrappers: flex-basis transition for slide effect */
.panel-wrapper {
  flex: 0 0 0px;
  overflow: hidden;
  transition: flex-basis 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.left-wrapper.is-expanded {
  flex: 0 0 20vw;
}

.center-wrapper.is-expanded {
  flex: 0 0 50vw;
}

/* Inner containers: fixed vw widths, never shrink */
.panel-inner {
  height: 100%;
  overflow: hidden;
  background-color: var(--panel-bg);
  border-right: 1px solid var(--panel-border);
}

.left-inner {
  width: 20vw;
}

.center-inner {
  width: 50vw;
}

/* Right column: takes remaining space */
.right-panel {
  flex: 1;
  min-width: 320px;
  overflow: hidden;
  background-color: var(--app-bg);
}

/* Theme toggle */
.theme-toggle {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2000;
  box-shadow: var(--shadow);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
}
::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>
