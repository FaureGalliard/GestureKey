import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://v2.tauri.app/start/frontend/vite/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true, // the engine only accepts this origin in dev
    watch: { ignored: ["**/src-tauri/**"] },
  },
  build: {
    rollupOptions: {
      // two windows: the app and the feedback overlay
      input: {
        main: "index.html",
        overlay: "overlay.html",
      },
    },
  },
});
