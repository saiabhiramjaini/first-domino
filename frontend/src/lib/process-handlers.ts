import { log } from "./log";

type ProcessHandlerFlag = { __firstDominoProcessHandlers?: boolean };

export function attachProcessHandlers(): void {
  const flag = globalThis as typeof globalThis & ProcessHandlerFlag;
  if (flag.__firstDominoProcessHandlers) return;
  flag.__firstDominoProcessHandlers = true;
  process.on("uncaughtException", (err) => {
    log.fatal({ err }, "process.uncaught_exception");
  });
  process.on("unhandledRejection", (reason) => {
    log.error(
      { err: reason instanceof Error ? reason : new Error(String(reason)) },
      "process.unhandled_rejection"
    );
  });
}
