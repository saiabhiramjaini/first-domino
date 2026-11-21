"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

type CopyButtonProps = { value: string; label: string };

// How long "Copied" shows before the button reads "Copy" again.
const COPIED_MS = 2_000;

export function CopyButton({ value, label }: CopyButtonProps) {
  const [hasCopied, setHasCopied] = useState(false);
  const resetTimer = useRef<number | undefined>(undefined);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setHasCopied(true);
      window.clearTimeout(resetTimer.current);
      resetTimer.current = window.setTimeout(() => setHasCopied(false), COPIED_MS);
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
