"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { useFlagRun } from "@/hooks/api/use-flag-run";
import { isApiError } from "@/lib/api-error";
import { reportClientError } from "@/lib/report-client-error";

import { FlagRunSchema, type FlagRunInput } from "../schema";

const NOT_FLAGGABLE = "Only a passed run that finished can be flagged.";

type FlagRunButtonProps = { runId: string };

export function FlagRunButton({ runId }: FlagRunButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const flagRun = useFlagRun();
  const form = useForm<FlagRunInput>({
    resolver: zodResolver(FlagRunSchema),
    defaultValues: { reason: "" },
  });

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (!open) form.reset();
  }

  async function onSubmit(values: FlagRunInput) {
    try {
      await flagRun.mutateAsync({ run_id: runId, reason: values.reason });
      toast.success("Run marked as failed. The diagnosis has started.");
      handleOpenChange(false);
    } catch (error) {
      if (isApiError(error, "conflict")) {
        form.setError("root", { message: NOT_FLAGGABLE });
        toast.error(`${NOT_FLAGGABLE} Reload the page to see this run's status.`);
        return;
      }
      reportClientError(error, "runs.flag");
      form.setError("root", { message: "Could not mark the run as failed. Try again." });
      toast.error("Could not mark the run as failed. Check that the API is running and try again.");
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button variant="outline" />}>Mark as failed</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <DialogHeader>
            <DialogTitle>Mark this run as failed?</DialogTitle>
            <DialogDescription>
              Your success check passed this run. Say what went wrong and it is diagnosed right
              away. Its replays are judged by a model against what you write here.
            </DialogDescription>
          </DialogHeader>
          <Controller
            name="reason"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="flag-run-reason">What went wrong?</FieldLabel>
                <Textarea
                  {...field}
                  id="flag-run-reason"
                  rows={4}
                  placeholder="The user said the refund was $100 but policy allows $20"
                  aria-invalid={fieldState.invalid}
                />
                <FieldDescription>
                  Write it as you would report it: a user complaint, a review note, a ticket.
                </FieldDescription>
                <FieldError errors={[fieldState.error]} />
                {form.formState.errors.root && (
                  <FieldError>{form.formState.errors.root.message}</FieldError>
                )}
              </Field>
            )}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={flagRun.isPending}>
              {flagRun.isPending ? "Marking..." : "Mark as failed and diagnose"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
