"use client";

import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { formatRelative } from "@/lib/format";
import { pageItems } from "@/lib/paging";

import { API_KEY_STATE, apiKeyState } from "./api-key-state";
import { CreateApiKeyForm } from "./create-api-key-form";
import { RevokeApiKeyButton } from "./revoke-api-key-button";

export type CreatedApiKey = { name: string; secret: string };

function ApiKeyList() {
  const apiKeys = useListApiKeys();
  const items = pageItems(apiKeys.data);

  if (apiKeys.isError) {
    return (
      <div className="border-t p-4">
        <QueryError
          error={apiKeys.error}
          what="API keys"
          source="settings.load_api_keys"
          onRetry={() => void apiKeys.refetch()}
        />
      </div>
    );
  }
  if (apiKeys.isPending) {
    return (
      <div className="border-t p-4">
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }
  if (items.length === 0) return null;

  return (
    <div className="flex flex-col border-t">
      <ul className="flex flex-col divide-y" aria-label="Your API keys">
        {items.map((apiKey) => {
          const state = apiKeyState(apiKey);
          return (
            <li key={apiKey.id} className="flex min-h-14 items-center gap-3 px-4 py-2.5">
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate text-sm font-medium">{apiKey.name}</span>
                <span className="font-mono text-xs text-muted-foreground">
                  {apiKey.prefix}… ·{" "}
                  {apiKey.last_used_at
                    ? `used ${formatRelative(apiKey.last_used_at)}`
                    : "never used"}
                </span>
              </div>
              <StatusBadge status={API_KEY_STATE[state]} />
              {state === "active" && <RevokeApiKeyButton apiKey={apiKey} />}
            </li>
          );
        })}
      </ul>
      {apiKeys.hasNextPage && (
        <div className="border-t p-2">
          <LoadMoreButton
            hasNextPage={apiKeys.hasNextPage}
            isFetchingNextPage={apiKeys.isFetchingNextPage}
            onLoadMore={() => void apiKeys.fetchNextPage()}
          />
        </div>
      )}
    </div>
  );
}

type ApiKeysProps = { onCreated: (createdKey: CreatedApiKey) => void };

// Create a project key and see the existing ones. The caller shows the new key's secret,
// once, in a dialog that must outlive this list (see SetupSteps).
export function ApiKeys({ onCreated }: ApiKeysProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="p-4">
        <CreateApiKeyForm onCreated={onCreated} />
      </div>
      <ApiKeyList />
    </div>
  );
}
