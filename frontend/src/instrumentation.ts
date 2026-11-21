import type { Instrumentation } from "next";

// Node-only modules are imported inside the runtime check so the Edge bundle never includes Pino.
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { registerNode } = await import("./instrumentation-node");
    registerNode();
  }
}

export const onRequestError: Instrumentation.onRequestError = async (err, request, context) => {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { logRequestError } = await import("./instrumentation-node");
    logRequestError(err, { request, route: context });
  }
};
