import { z } from "zod";

import { zFlagRunRequest } from "@/api/generated/zod.gen";

// The API's cap on a flag reason; the test keeps it equal to the generated schema's.
export const FLAG_REASON_MAX = 2000;

export const FlagRunSchema = z.object({
  reason: z
    .string({ message: "Say what went wrong" })
    .trim()
    .min(1, { message: "Say what went wrong" })
    .max(FLAG_REASON_MAX, {
      message: `Keep it to ${FLAG_REASON_MAX} characters or fewer`,
    })
    .pipe(zFlagRunRequest.shape.reason),
});
export type FlagRunInput = z.infer<typeof FlagRunSchema>;
