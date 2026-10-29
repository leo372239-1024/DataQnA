import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// DataQnA frontend build config.
// - dev server proxies /api to the FastAPI backend so SSE + REST share one origin.
// - vitest config is inlined (jsdom, setup file).
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // 按 vendor 分包，避免 antd + echarts 打成单个 2MB chunk，改善首屏加载与长期缓存
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          antd: ["antd", "@ant-design/icons"],
          charts: ["echarts"],
          query: ["@tanstack/react-query", "zustand"],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
});
