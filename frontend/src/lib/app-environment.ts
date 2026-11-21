export const APP_ENVIRONMENTS = ["local", "dev", "prod"] as const;
export type AppEnvironment = (typeof APP_ENVIRONMENTS)[number];
export type EnvironmentSettings = { enableBrowserSourceMaps: boolean };

export const ENVIRONMENT_SETTINGS: Record<AppEnvironment, EnvironmentSettings> = {
  local: { enableBrowserSourceMaps: true },
  dev: { enableBrowserSourceMaps: true },
  prod: { enableBrowserSourceMaps: false },
};

function isAppEnvironment(value: string | undefined): value is AppEnvironment {
  return APP_ENVIRONMENTS.some((environment) => environment === value);
}

export function appEnvironment(value: string | undefined): AppEnvironment {
  return isAppEnvironment(value) ? value : "local";
}
