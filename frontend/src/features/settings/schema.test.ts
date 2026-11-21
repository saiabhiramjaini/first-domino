import { describe, expect, it } from "vitest";

import { CreateApiKeySchema, SlackWebhookSchema } from "./schema";

describe("CreateApiKeySchema", () => {
  it("trims the name", () => {
    const parsed = CreateApiKeySchema.safeParse({ name: "  Demo agent  " });
    expect(parsed.success && parsed.data.name).toBe("Demo agent");
  });

  it("rejects a blank name with a readable message", () => {
    const parsed = CreateApiKeySchema.safeParse({ name: "   " });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe("Name is required");
  });

  it("rejects a name over 120 characters", () => {
    expect(CreateApiKeySchema.safeParse({ name: "a".repeat(121) }).success).toBe(false);
    expect(CreateApiKeySchema.safeParse({ name: "a".repeat(120) }).success).toBe(true);
  });
});

describe("SlackWebhookSchema", () => {
  it("accepts an https URL", () => {
    const parsed = SlackWebhookSchema.safeParse({
      webhook_url: " https://hooks.slack.com/services/T000/B000/XXXX ",
    });
    expect(parsed.success && parsed.data.webhook_url).toBe(
      "https://hooks.slack.com/services/T000/B000/XXXX"
    );
  });

  it("rejects an empty value, plain http and non-URLs", () => {
    expect(SlackWebhookSchema.safeParse({ webhook_url: "" }).error?.issues[0]?.message).toBe(
      "Webhook URL is required"
    );
    expect(SlackWebhookSchema.safeParse({ webhook_url: "http://hooks.slack.com/x" }).success).toBe(
      false
    );
    expect(SlackWebhookSchema.safeParse({ webhook_url: "not a url" }).success).toBe(false);
  });
});
