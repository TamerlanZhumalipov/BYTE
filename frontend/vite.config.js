import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../static/react",
    emptyOutDir: true,
    manifest: true,
    rolldownOptions: {
      input: fileURLToPath(new URL("./src/main.jsx", import.meta.url)),
    },
  },
  test: { environment: "jsdom", restoreMocks: true },
});
