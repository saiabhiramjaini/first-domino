import { z } from "zod";

const API_KEY_NAME_MAX = 120;
const WEBHOOK_URL_MAX = 2083;

function isHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

export const CreateApiKeySchema = z.object({
  name: z
    .string({ message: "Name is required" })
    .trim()
    .min(1, { message: "Name is required" })
    .max(API_KEY_NAME_MAX, { message: `Name must be ${API_KEY_NAME_MAX} characters or fewer` }),
});
export type CreateApiKeyInput = z.infer<typeof CreateApiKeySchema>;

export const SlackWebhookSchema = z.object({
  webhook_url: z
    .string({ message: "Webhook URL is required" })
    .trim()
    .min(1, { message: "Webhook URL is required" })
    .max(WEBHOOK_URL_MAX, { message: "Webhook URL is too long" })
    .refine(isHttpsUrl, { message: "Enter a full https:// URL from Slack" }),
});
export type SlackWebhookInput = z.infer<typeof SlackWebhookSchema>;
