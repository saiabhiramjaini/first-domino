import pino, { type Logger, type LoggerOptions } from "pino";

const isProd = process.env.NODE_ENV === "production";
const isTest = process.env.NODE_ENV === "test";

const PINO_TO_SEVERITY: Record<string, string> = {
  trace: "DEBUG",
  debug: "DEBUG",
  info: "INFO",
  warn: "WARNING",
  error: "ERROR",
  fatal: "CRITICAL",
};

const baseOptions: LoggerOptions = {
  level: process.env.LOG_LEVEL ?? (isProd ? "info" : "debug"),
  serializers: { err: pino.stdSerializers.err, error: pino.stdSerializers.err },
  formatters: {
    level(label) {
      return { level: label, severity: PINO_TO_SEVERITY[label] ?? label.toUpperCase() };
    },
    bindings() {
      return { service: process.env.DD_SERVICE ?? "first-domino-web" };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: {
    paths: [
      "password",
      "*.password",
      "token",
      "*.token",
      "apiKey",
      "*.apiKey",
      "authorization",
      "*.authorization",
      "headers.authorization",
      "headers.cookie",
    ],
    censor: "[REDACTED]",
    remove: false,
  },
};

const devTransport: LoggerOptions["transport"] =
  !isProd && !isTest
    ? {
        target: "pino-pretty",
        options: {
          colorize: true,
          translateTime: "SYS:HH:MM:ss.l",
          ignore: "pid,hostname,service,severity",
        },
      }
    : undefined;

function buildDestination(): pino.DestinationStream | undefined {
  const appLogFile = process.env.APP_LOG_FILE;
  if (!appLogFile || devTransport) return undefined;
  try {
    const fileStream = pino.destination({ dest: appLogFile, mkdir: true, sync: false });
    // A broken log file must not crash the server; stdout still gets every line.
    fileStream.on("error", () => {});
    return pino.multistream([
      { stream: pino.destination({ dest: 1, sync: false }) },
      { stream: fileStream },
    ]);
  } catch (err) {
    process.stderr.write(
      `[log] APP_LOG_FILE unusable, stdout only: ${err instanceof Error ? err.message : String(err)}\n`
    );
    return undefined;
  }
}

const destination = buildDestination();

export const log: Logger = devTransport
  ? pino({ ...baseOptions, transport: devTransport })
  : destination
    ? pino(baseOptions, destination)
    : pino(baseOptions);
