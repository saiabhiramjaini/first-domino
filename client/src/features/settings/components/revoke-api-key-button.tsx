"use client";

import { useState } from "react";
import { toast } from "sonner";

import type { ApiKey } from "@/api/generated";
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
import { useRevokeApiKey } from "@/hooks/api/use-revoke-api-key";
import { reportClientError } from "@/lib/report-client-error";

type RevokeApiKeyButtonProps = { apiKey: Pick<ApiKey, "id" | "name" | "prefix"> };

export function RevokeApiKeyButton({ apiKey }: RevokeApiKeyButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const revokeApiKey = useRevokeApiKey();

  async function handleRevoke() {
    try {
      await revokeApiKey.mutateAsync(apiKey.id);
      toast.success(`API key "${apiKey.name}" revoked`);
      setIsOpen(false);
    } catch (error) {
      reportClientError(error, "settings.revoke_api_key");
      toast.error("Could not revoke the key. Try again in a moment.");
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button variant="ghost" size="sm" />}>Revoke</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Revoke &quot;{apiKey.name}&quot;?</DialogTitle>
          <DialogDescription>
            Agents and workers using the key starting with {apiKey.prefix} stop working right away.
            You cannot undo this.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Keep key
          </Button>
          <Button variant="destructive" onClick={handleRevoke} disabled={revokeApiKey.isPending}>
            {revokeApiKey.isPending ? "Revoking..." : "Revoke key"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
