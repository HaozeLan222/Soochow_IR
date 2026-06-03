<template>
  <div class="info-display">
    <el-empty
      v-if="!store.hasSelectedTeachers"
      :image-size="100"
      description="在右侧选择教师查看详情"
    >
      <template #image>
        <el-icon :size="60" color="var(--empty-color)"><User /></el-icon>
      </template>
    </el-empty>
    <el-scrollbar v-else class="detail-scroll">
      <TransitionGroup name="detail-card" tag="div">
        <TeacherDetailCard
          v-for="teacher in store.selectedTeachers"
          :key="teacher.doc_id"
          :teacher="teacher"
        />
      </TransitionGroup>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { useSearchStore } from "../stores/search.js";
import TeacherDetailCard from "./TeacherDetailCard.vue";
import { User } from "@element-plus/icons-vue";

const store = useSearchStore();
</script>

<style scoped>
.info-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--app-bg);
}

.detail-scroll {
  flex: 1;
  margin: 0 16px;
  position: relative;
}

.detail-card-enter-active,
.detail-card-leave-active {
  transition: all 0.3s ease;
}

.detail-card-enter-from,
.detail-card-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

.detail-card-leave-active {
  position: absolute;
  width: 100%;
}

.detail-card-move {
  transition: transform 0.3s ease;
}
</style>
