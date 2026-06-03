<template>
  <el-card class="detail-card" shadow="never" body-style="padding: 20px">
    <div class="header">
      <el-avatar
        :size="80"
        :src="teacher.photo_url || defaultAvatar"
        :icon="User"
        shape="square"
        style="border-radius: 8px"
      />
      <div class="header-info">
        <div class="name-row">
          <span class="name">{{ teacher.name }}</span>
          <el-tag v-if="teacher.title" type="primary" effect="dark" size="small">
            {{ teacher.title }}
          </el-tag>
          <el-tag v-if="teacher.college" type="info" size="small">
            {{ teacher.college }}
          </el-tag>
        </div>
        <div class="contact-row">
          <span v-if="teacher.email" class="contact-item">
            <el-icon><Message /></el-icon>
            {{ teacher.email }}
          </span>
          <span v-if="teacher.phone" class="contact-item">
            <el-icon><Phone /></el-icon>
            {{ teacher.phone }}
          </span>
          <span v-if="teacher.url" class="contact-item">
            <el-icon><Link /></el-icon>
            <a :href="teacher.url" target="_blank" rel="noopener">主页</a>
          </span>
        </div>
      </div>
    </div>

    <el-divider />

    <div v-if="teacher.research" class="section">
      <h4 class="section-title">
        <el-icon><Reading /></el-icon>
        研究方向
      </h4>
      <p class="section-body">{{ teacher.research }}</p>
    </div>

    <div v-if="teacher.papers" class="section">
      <h4 class="section-title">
        <el-icon><Document /></el-icon>
        代表论文
      </h4>
      <p class="section-body">{{ teacher.papers }}</p>
    </div>

    <div v-if="teacher.profile" class="section">
      <h4 class="section-title">
        <el-icon><User /></el-icon>
        个人简介
      </h4>
      <p class="section-body">{{ teacher.profile }}</p>
    </div>

    <div v-if="teacher.matched_terms?.length" class="section">
      <h4 class="section-title">
        <el-icon><Check /></el-icon>
        匹配词
      </h4>
      <div class="tags-row">
        <el-tag
          v-for="term in teacher.matched_terms"
          :key="term"
          type="success"
          size="small"
          effect="dark"
        >
          {{ term }}
        </el-tag>
      </div>
    </div>

    <div v-if="teacher.score" class="score-badge">
      相关度: {{ teacher.score.toFixed(2) }}
    </div>
  </el-card>
</template>

<script setup>
import { User, Message, Phone, Link, Reading, Document, Check } from "@element-plus/icons-vue";

defineProps({
  teacher: { type: Object, required: true },
});

const defaultAvatar = "https://cube.elemecdn.com/3/7c/3ea6be4d8b6a68f1f0e6e6e6e6e6e6e6.png";
</script>

<style scoped>
.detail-card {
  margin-bottom: 16px;
  background-color: var(--card-bg);
  border-color: var(--panel-border);
  transition: background-color 0.3s ease;
}

.detail-card:last-child {
  margin-bottom: 0;
}

.header {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.name {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.contact-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.contact-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.contact-item a {
  color: var(--accent-color);
  text-decoration: none;
}

.contact-item a:hover {
  text-decoration: underline;
}

.section {
  margin-top: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.section-body {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.score-badge {
  margin-top: 16px;
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.1);
  color: var(--accent-color);
  font-size: 12px;
  font-weight: 600;
}
</style>
