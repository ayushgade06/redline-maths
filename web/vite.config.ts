import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { chunkSizeWarningLimit: 650 }, // KaTeX is needed on first paint (landing hero)
  server: { proxy: { "/api": "http://localhost:8787" } },
});
