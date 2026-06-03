<template>
  <div class="search-stack">
    <div class="panel-title">搜索栈</div>
    <el-scrollbar class="stack-list">
      <div
        v-for="session in store.sessions"
        :key="session.id"
        class="stack-item"
        :class="{ active: session.id === store.activeSessionId }"
        @click="store.switchSession(session.id)"
      >
        <div class="query-text">{{ session.query }}</div>
        <div class="meta-row">
          <el-tag size="small" effect="plain">{{ session.field }}</el-tag>
          <span class="count">{{ session.results.length }} 条</span>
        </div>
        <el-button
          v-if="session.id === store.activeSessionId"
          class="close-btn"
          text
          circle
          size="small"
          @click.stop="store.removeSession(session.id)"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { useSearchStore } from "../stores/search.js";
import { Close } from "@element-plus/icons-vue";

const store = useSearchStore();
</script>

<style scoped>
.search-stack {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--panel-bg);
}

.panel-title {
  padding: 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--panel-border);
  flex-shrink: 0;
}

.stack-list {
  flex: 1;
}

.stack-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--panel-border);
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
}

.stack-item:hover {
  background-color: var(--card-hover);
}

.stack-item.active {
  background-color: var(--card-hover);
  border-left: 3px solid var(--accent-color);
  padding-left: 13px;
}

.query-text {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 6px;
  word-break: break-all;
  padding-right: 24px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.count {
  font-size: 12px;
  color: var(--text-muted);
}

.close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  color: var(--text-muted);
}
.close-btn:hover {
  color: #f56c6c;
}
</style>
