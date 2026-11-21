import type { NextConfig } from "next";

import { ENVIRONMENT_SETTINGS, appEnvironment } from "./src/lib/app-environment";

const environment = ENVIRONMENT_SETTINGS[appEnvironment(process.env.APP_ENV)];

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  productionBrowserSourceMaps: environment.enableBrowserSourceMaps,
  serverExternalPackages: ["pino"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
