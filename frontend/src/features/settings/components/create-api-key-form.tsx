"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useCreateApiKey } from "@/hooks/api/use-create-api-key";
import { reportClientError } from "@/lib/report-client-error";

import { CreateApiKeySchema, type CreateApiKeyInput } from "../schema";

type CreateApiKeyFormProps = {
  onCreated: (createdKey: { name: string; secret: string }) => void;
};

export function CreateApiKeyForm({ onCreated }: CreateApiKeyFormProps) {
  const createApiKey = useCreateApiKey();
  const form = useForm<CreateApiKeyInput>({
    resolver: zodResolver(CreateApiKeySchema),
    defaultValues: { name: "" },
  });

  async function onSubmit(values: CreateApiKeyInput) {
    try {
      const created = await createApiKey.mutateAsync(values);
      toast.success(`API key "${created.api_key.name}" created`);
      form.reset();
      onCreated({ name: created.api_key.name, secret: created.secret });
    } catch (error) {
      reportClientError(error, "settings.create_api_key");
      form.setError("root", { message: "Could not create the key. Try again." });
      toast.error("Could not create the API key. Try again in a moment.");
    }
  }

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="flex flex-col gap-3 sm:flex-row sm:items-start"
      noValidate
    >
      <Controller
        name="name"
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid} className="flex-1">
            <FieldLabel htmlFor="api-key-name" className="sr-only">
              Key name
            </FieldLabel>
            <Input
              {...field}
              id="api-key-name"
              placeholder="Key name, for example Demo agent"
              aria-invalid={fieldState.invalid}
              autoComplete="off"
            />
            <FieldError errors={[fieldState.error]} />
            {form.formState.errors.root && (
              <FieldError>{form.formState.errors.root.message}</FieldError>
            )}
          </Field>
        )}
      />
      <Button type="submit" disabled={createApiKey.isPending}>
        {createApiKey.isPending ? "Creating..." : "Create API key"}
      </Button>
    </form>
  );
}
