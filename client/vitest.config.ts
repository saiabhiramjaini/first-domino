import path from "path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    env: {
      NEXT_PUBLIC_APP_URL: "https://app.test",
      NEXT_PUBLIC_API_URL: "https://api.test",
    },
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
