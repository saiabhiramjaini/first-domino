import "server-only";

import nodemailer from "nodemailer";

import { log } from "@/lib/log";
import type { MailSender } from "@/lib/server-env";

export type Email = { to: string; subject: string; text: string };

// Sends one plain-text email through Gmail. A failure is logged and reported as false.
export async function sendEmail(sender: MailSender, email: Email): Promise<boolean> {
  const transporter = nodemailer.createTransport({
    service: "gmail",
    auth: { user: sender.user, pass: sender.pass },
  });
  try {
    await transporter.sendMail({ from: `First Domino <${sender.user}>`, ...email });
    return true;
  } catch (err) {
    log.error({ err }, "email.send_failed");
    return false;
  }
}
