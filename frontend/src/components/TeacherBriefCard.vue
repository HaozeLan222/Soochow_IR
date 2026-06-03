<template>
  <el-card
    :class="{ 'is-selected': selected }"
    shadow="hover"
    body-style="padding: 12px"
    @click="$emit('click')"
  >
    <div class="brief-content">
      <el-avatar
        :size="44"
        :src="teacher.photo_url || defaultAvatar"
        :icon="User"
      />
      <div class="info">
        <div class="name-row">
          <span class="name">{{ teacher.name }}</span>
          <span v-if="teacher.score" class="score">{{ teacher.score.toFixed(1) }}</span>
        </div>
        <el-tag size="small" effect="plain" type="info">{{ teacher.college }}</el-tag>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { User } from "@element-plus/icons-vue";

defineProps({
  teacher: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});

defineEmits(["click"]);

const defaultAvatar = "https://cube.elemecdn.com/3/7c/3ea6be4d8b6a68f1f0e6e6e6e6e6e6e6.png";
</script>

<style scoped>
.brief-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score {
  font-size: 12px;
  color: var(--accent-color);
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 4px;
}

.el-card {
  cursor: pointer;
  transition: all 0.2s;
  background-color: var(--card-bg);
  border-color: var(--panel-border);
  width: min-content;
}

.el-card:hover {
  background-color: var(--card-hover);
}

.el-card.is-selected {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}
</style>
