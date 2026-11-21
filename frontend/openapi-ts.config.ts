import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: process.env.OPENAPI_INPUT ?? "../api/openapi.json",
  output: { path: "src/api/generated" },
  plugins: ["@hey-api/client-fetch", "@hey-api/typescript", "@hey-api/sdk", "zod"],
});
