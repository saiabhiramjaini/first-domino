"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

type CopyButtonProps = { value: string; label: string };

export function CopyButton({ value, label }: CopyButtonProps) {
  const [hasCopied, setHasCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setHasCopied(true);
      toast.success("Copied to the clipboard");
    } catch (error) {
      reportClientError(error, "settings.copy");
      toast.error("Could not copy. Select the text and copy it by hand.");
    }
  }

  return (
    <Button variant="ghost" size="xs" onClick={handleCopy} aria-label={label}>
      {hasCopied ? <CheckIcon aria-hidden="true" /> : <CopyIcon aria-hidden="true" />}
      {hasCopied ? "Copied" : "Copy"}
    </Button>
  );
}
