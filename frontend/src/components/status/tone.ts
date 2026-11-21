import type { badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

export type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "domino";

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

export const TONE_BADGE_VARIANT = {
  neutral: "muted",
  info: "info",
  success: "success",
  warning: "warning",
  danger: "destructive",
  domino: "domino",
} as const satisfies Record<Tone, BadgeVariant>;

export type ToneLabel = { tone: Tone; label: string };
