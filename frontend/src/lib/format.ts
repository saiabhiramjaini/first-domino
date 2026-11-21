const LOCALE = "en-US";

const dateTime = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short" });
const integer = new Intl.NumberFormat(LOCALE);
const percent = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 0 });
const usd = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});
const seconds = new Intl.NumberFormat(LOCALE, {
  style: "unit",
  unit: "second",
  unitDisplay: "short",
  maximumFractionDigits: 1,
});
const relative = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });

const RELATIVE_STEPS: ReadonlyArray<[Intl.RelativeTimeFormatUnit, number]> = [
  ["second", 60],
  ["minute", 60],
  ["hour", 24],
  ["day", 7],
  ["week", 4.35],
  ["month", 12],
  ["year", Number.POSITIVE_INFINITY],
];

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

export function formatRelative(iso: string, now: Date = new Date()): string {
  let value = (new Date(iso).getTime() - now.getTime()) / 1000;
  for (const [unit, size] of RELATIVE_STEPS) {
    if (Math.abs(value) < size) return relative.format(Math.round(value), unit);
    value /= size;
  }
  return dateTime.format(new Date(iso));
}

export function formatInteger(value: number): string {
  return integer.format(value);
}

export function formatPercent(ratio: number): string {
  return percent.format(ratio);
}

export function formatUsd(value: number): string {
  return usd.format(value);
}

export function formatSeconds(value: number): string {
  return seconds.format(value);
}
