import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

export async function searchTeachers(params) {
  const response = await api.get("/search", { params });
  return response.data;
}

export async function getTeacher(docId) {
  const response = await api.get(`/teachers/${docId}`);
  return response.data;
}

export async function getStats() {
  const response = await api.get("/stats");
  return response.data;
}
