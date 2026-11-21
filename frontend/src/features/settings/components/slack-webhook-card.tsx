"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import type { ToneLabel } from "@/components/status/tone";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetProjectSelf } from "@/hooks/api/use-get-project-self";
import { useSetProjectSlackWebhook } from "@/hooks/api/use-set-project-slack-webhook";
import { isApiError } from "@/lib/api-error";
import { reportClientError } from "@/lib/report-client-error";

import { SlackWebhookSchema, type SlackWebhookInput } from "../schema";

const WEBHOOK_STATE = {
  set: { tone: "success", label: "Connected" },
  unset: { tone: "neutral", label: "Not connected" },
} as const satisfies Record<"set" | "unset", ToneLabel>;

export function SlackWebhookCard() {
  const project = useGetProjectSelf();
  const setWebhook = useSetProjectSlackWebhook();
  const form = useForm<SlackWebhookInput>({
    resolver: zodResolver(SlackWebhookSchema),
    defaultValues: { webhook_url: "" },
  });

  async function onSubmit(values: SlackWebhookInput) {
    try {
      await setWebhook.mutateAsync({ webhook_url: values.webhook_url });
      toast.success("Slack alerts are on. New root causes will post to your channel.");
      form.reset();
    } catch (error) {
      reportClientError(error, "settings.set_slack_webhook");
      if (isApiError(error, "validation_failed")) {
        form.setError("webhook_url", { message: "Slack did not accept this URL. Copy it again." });
      } else {
        form.setError("root", { message: "Could not save the webhook. Try again." });
      }
      toast.error("Could not save the Slack webhook. Check the URL and try again.");
    }
  }

  async function handleRemove() {
    try {
      await setWebhook.mutateAsync({ webhook_url: null });
      toast.success("Slack webhook removed. Alerts are off.");
    } catch (error) {
      reportClientError(error, "settings.remove_slack_webhook");
      toast.error("Could not remove the webhook. Try again in a moment.");
    }
  }

  const isSet = project.data?.slack_webhook_set ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Slack alerts</CardTitle>
        <CardDescription>
          Post a message to Slack when a diagnosis finds a new root cause.
        </CardDescription>
        <CardAction>
          {project.data ? (
            <StatusBadge status={isSet ? WEBHOOK_STATE.set : WEBHOOK_STATE.unset} />
          ) : (
            <Skeleton className="h-5 w-24" />
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {project.isError && (
          <QueryError
            error={project.error}
            what="your Slack settings"
            source="settings.load_project"
            onRetry={() => void project.refetch()}
          />
        )}
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3" noValidate>
          <Controller
            name="webhook_url"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="slack-webhook-url">
                  {isSet ? "Replace the webhook URL" : "Webhook URL"}
                </FieldLabel>
                <Input
                  {...field}
                  id="slack-webhook-url"
                  type="url"
                  inputMode="url"
                  placeholder="https://hooks.slack.com/services/…"
                  aria-invalid={fieldState.invalid}
                  autoComplete="off"
                />
                <FieldDescription>
                  Create an incoming webhook in Slack and paste its URL. It is stored and never
                  shown again.
                </FieldDescription>
                <FieldError errors={[fieldState.error]} />
                {form.formState.errors.root && (
                  <FieldError>{form.formState.errors.root.message}</FieldError>
                )}
              </Field>
            )}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" disabled={setWebhook.isPending}>
              {setWebhook.isPending ? "Saving..." : "Save webhook"}
            </Button>
            {isSet && (
              <Button
                type="button"
                variant="outline"
                onClick={handleRemove}
                disabled={setWebhook.isPending}
              >
                Remove webhook
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
