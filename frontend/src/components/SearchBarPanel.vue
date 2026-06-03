<template>
  <div class="search-panel">
    <div class="content-wrapper">
      <!-- Results area (shown when has results) -->
      <div v-if="store.hasSearchResults" class="results-area">
        <el-scrollbar>
          <div class="results-header">
            <span class="results-count">
              找到 {{ store.activeSession.results.length }} 位教师
            </span>
            <el-dropdown @command="handleSort">
              <el-button size="small" text>
                <el-icon><Sort /></el-icon>
                {{ sortLabel }}
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="relevance">相关度</el-dropdown-item>
                  <el-dropdown-item command="name">姓名</el-dropdown-item>
                  <el-dropdown-item command="college">学院</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="results-grid">
            <TeacherBriefCard
              v-for="teacher in store.sortedResults"
              :key="teacher.doc_id"
              :teacher="teacher"
              :selected="isSelected(teacher.doc_id)"
              @click="store.toggleSelection(teacher.doc_id)"
            />
          </div>
        </el-scrollbar>
      </div>

      <!-- Search controls -->
      <div class="search-controls" :class="{ centered: !store.hasSearchResults }">
        <div v-if="!store.hasSearchResults" class="brand">
          <div class="brand-title">苏大教师检索</div>
          <div class="brand-sub">Soochow University Faculty IR</div>
        </div>

        <el-input
          v-model="query"
          placeholder="输入搜索内容..."
          size="large"
          clearable
          @keyup.enter="search"
        >
          <template #append>
            <el-button type="primary" @click="search">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>

        <div class="field-group">
          <el-radio-group v-model="field" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="name">姓名</el-radio-button>
            <el-radio-button label="college">学院</el-radio-button>
            <el-radio-button label="research">研究方向</el-radio-button>
          </el-radio-group>
        </div>

        <div class="topk-row">
          <span class="topk-label">结果数 {{ topK }}</span>
          <el-slider v-model="topK" :min="5" :max="50" :step="5" show-stops />
        </div>

        <el-button type="primary" style="width: 100%" size="large" @click="search">
          搜索
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useSearchStore } from "../stores/search.js";
import TeacherBriefCard from "./TeacherBriefCard.vue";
import { Search, Sort, ArrowDown } from "@element-plus/icons-vue";

const store = useSearchStore();
const query = ref("");
const field = ref("all");
const topK = ref(10);

const sortLabel = computed(() => {
  const map = { relevance: "相关度", name: "姓名", college: "学院" };
  return map[store.sortMode] || "相关度";
});

function handleSort(command) {
  store.setSortMode(command);
}

function isSelected(docId) {
  const s = store.activeSession;
  return s ? s.selectedIds.includes(docId) : false;
}

async function search() {
  if (!query.value.trim()) return;
  await store.executeSearch(query.value.trim(), field.value, topK.value);
}
</script>

<style scoped>
.search-panel {
  height: 100%;
}

.content-wrapper {
  width: 100%;
  height: 100%;
  max-width: 40vw;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

/* Results area */
.results-area {
  flex: 1;
  overflow: hidden;
  background-color: var(--app-bg);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px 4px;
}

.results-count {
  font-size: 13px;
  color: var(--text-secondary);
}

.results-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 16px 16px;
}

/* Search controls */
.search-controls {
  padding: 20px;
  background-color: var(--panel-bg);
  border-top: 1px solid var(--panel-border);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-controls.centered {
  flex: 1;
  justify-content: center;
  border-top: none;
  background-color: transparent;
}

.brand {
  text-align: center;
  margin-bottom: 24px;
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 2px;
}

.brand-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 6px;
  letter-spacing: 1px;
}

.field-group {
  display: flex;
  justify-content: center;
}

.topk-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.topk-label {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
