import { z } from "zod";

const API_KEY_NAME_MAX = 120;

export const CreateApiKeySchema = z.object({
  name: z
    .string({ message: "Name is required" })
    .trim()
    .min(1, { message: "Name is required" })
    .max(API_KEY_NAME_MAX, { message: `Name must be ${API_KEY_NAME_MAX} characters or fewer` }),
});
export type CreateApiKeyInput = z.infer<typeof CreateApiKeySchema>;
