import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

export async function searchTeachers(params, engine = "bm25") {
  const response = await api.post(`/search?engine=${encodeURIComponent(engine)}`, params);
  return response.data;
}

export async function getStats() {
  const response = await api.get("/stats");
  return response.data;
}
