import { defineStore } from "pinia";
import { searchTeachers } from "../api/search.js";

export const useSearchStore = defineStore("search", {
  state: () => ({
    sessions: [],
    activeSessionId: null,
    sortMode: "relevance", // 'relevance' | 'name' | 'college'
    theme: "light", // 'light' | 'dark'
    engine: "bm25", // 'bm25' | 'optimized'
  }),

  getters: {
    activeSession: (state) =>
      state.sessions.find((s) => s.id === state.activeSessionId) || null,

    hasSessions: (state) => state.sessions.length > 0,

    hasSearchResults: (state) => {
      const s = state.sessions.find((s) => s.id === state.activeSessionId);
      return s ? s.results.length > 0 : false;
    },

    hasSelectedTeachers: (state) => {
      const s = state.sessions.find((s) => s.id === state.activeSessionId);
      return s ? s.selectedIds.length > 0 : false;
    },

    sortedResults: (state) => {
      const s = state.sessions.find((s) => s.id === state.activeSessionId);
      if (!s) return [];
      let results = [...s.results];
      if (state.sortMode === "name") {
        results.sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
      } else if (state.sortMode === "college") {
        results.sort(
          (a, b) =>
            a.college.localeCompare(b.college, "zh-CN") ||
            a.name.localeCompare(b.name, "zh-CN")
        );
      } else {
        // relevance: score desc
        results.sort((a, b) => b.score - a.score);
      }
      return results;
    },

    selectedTeachers: (state) => {
      const s = state.sessions.find((s) => s.id === state.activeSessionId);
      if (!s) return [];
      return s.selectedIds
        .map((id) => s.results.find((r) => r.doc_id === id))
        .filter(Boolean);
    },
  },

  actions: {
    async executeSearch(query, field = "all", topK = 10, engine = this.engine) {
      this.engine = engine;
      const data = await searchTeachers({ query, field, top_k: topK }, engine);
      const session = {
        id: crypto.randomUUID(),
        query,
        field,
        topK,
        engine,
        results: data.results || [],
        selectedIds: [],
        createdAt: Date.now(),
      };
      this.sessions.unshift(session);
      this.activeSessionId = session.id;
    },

    switchSession(id) {
      this.activeSessionId = id;
    },

    removeSession(id) {
      this.sessions = this.sessions.filter((s) => s.id !== id);
      if (this.activeSessionId === id) {
        this.activeSessionId =
          this.sessions.length > 0 ? this.sessions[0].id : null;
      }
    },

    toggleSelection(docId) {
      const s = this.sessions.find((s) => s.id === this.activeSessionId);
      if (!s) return;
      const idx = s.selectedIds.indexOf(docId);
      if (idx >= 0) {
        s.selectedIds.splice(idx, 1);
      } else {
        s.selectedIds.push(docId);
      }
    },

    setSortMode(mode) {
      this.sortMode = mode;
    },

    setEngine(engine) {
      this.engine = engine;
    },

    toggleTheme() {
      this.theme = this.theme === "light" ? "dark" : "light";
    },
  },

  persist: {
    key: "soochow-ir-search",
    paths: ["sessions", "theme", "engine"],
    beforeRestore: (context) => {
      // activeSessionId restored as-is; if session missing it'll be handled by getter
    },
  },
});
