<template>
  <div class="home">
    <h1>苏州大学导师信息检索</h1>
    <el-card class="status-card">
      <template #header>
        <span>后端连通性测试</span>
      </template>
      <el-button type="primary" @click="testConnection">测试连接</el-button>
      <div v-if="loading" style="margin-top: 12px">
        <el-icon class="is-loading"><Loading /></el-icon> 请求中...
      </div>
      <div v-if="result" style="margin-top: 12px">
        <el-tag type="success">连接成功</el-tag>
        <pre style="margin-top: 8px; background: #f5f7fa; padding: 12px; border-radius: 4px">{{ result }}</pre>
      </div>
      <div v-if="error" style="margin-top: 12px">
        <el-tag type="danger">连接失败</el-tag>
        <p style="color: #f56c6c; margin-top: 8px">{{ error }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Loading } from "@element-plus/icons-vue";
import { getStats } from "../api/search.js";

const loading = ref(false);
const result = ref(null);
const error = ref(null);

async function testConnection() {
  loading.value = true;
  result.value = null;
  error.value = null;
  try {
    const data = await getStats();
    result.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e.message || "请求失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f5f7fa;
}

h1 {
  color: #303133;
  margin-bottom: 24px;
}

.status-card {
  width: 480px;
}
</style>
