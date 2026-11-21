"use client";

import { TriangleAlertIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { CopyButton } from "./copy-button";

type CreatedApiKey = { name: string; secret: string };

type ApiKeySecretDialogProps = {
  createdKey: CreatedApiKey | null;
  onClose: () => void;
};

export function ApiKeySecretDialog({ createdKey, onClose }: ApiKeySecretDialogProps) {
  return (
    <Dialog
      open={createdKey !== null}
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Copy your new API key</DialogTitle>
          <DialogDescription>
            {createdKey ? `"${createdKey.name}" is ready. ` : ""}Set it as FIRST_DOMINO_API_KEY
            where your agent runs.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-start gap-2 rounded-lg bg-warning/25 p-3 text-sm text-warning-foreground">
          <TriangleAlertIcon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>This is the only time you will see this key. Store it somewhere safe now.</p>
        </div>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-lg border bg-muted px-3 py-2 font-mono text-xs">
            {createdKey?.secret}
          </code>
          {createdKey && <CopyButton value={createdKey.secret} label="Copy the API key" />}
        </div>
        <DialogFooter>
          <Button onClick={onClose}>Close, I saved it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
