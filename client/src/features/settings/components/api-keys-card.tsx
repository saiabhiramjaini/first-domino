"use client";

import { useState } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { LoadMoreButton } from "@/components/feedback/load-more-button";
import { QueryError } from "@/components/feedback/query-error";
import { StatusBadge } from "@/components/status/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useListApiKeys } from "@/hooks/api/use-list-api-keys";
import { formatDateTime, formatRelative } from "@/lib/format";
import { pageItems } from "@/lib/paging";

import { ApiKeySecretDialog } from "./api-key-secret-dialog";
import { API_KEY_STATE, apiKeyState } from "./api-key-state";
import { CreateApiKeyForm } from "./create-api-key-form";
import { RevokeApiKeyButton } from "./revoke-api-key-button";

type CreatedApiKey = { name: string; secret: string };

const SKELETON_ROWS = ["first", "second"] as const;

function ApiKeyList() {
  const apiKeys = useListApiKeys();
  const items = pageItems(apiKeys.data);

  if (apiKeys.isError) {
    return (
      <QueryError
        error={apiKeys.error}
        what="API keys"
        source="settings.load_api_keys"
        onRetry={() => void apiKeys.refetch()}
      />
    );
  }

  if (apiKeys.isPending) {
    return (
      <div className="flex flex-col gap-2">
        {SKELETON_ROWS.map((row) => (
          <Skeleton key={row} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="No API keys yet"
        description="Create a key above, then set it as FIRST_DOMINO_API_KEY where your agent runs."
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Key</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Last used</TableHead>
            <TableHead>State</TableHead>
            <TableHead>
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((apiKey) => {
            const state = apiKeyState(apiKey);
            return (
              <TableRow key={apiKey.id}>
                <TableCell className="font-medium">{apiKey.name}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {apiKey.prefix}…
                </TableCell>
                <TableCell>{formatDateTime(apiKey.created_at)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {apiKey.last_used_at ? formatRelative(apiKey.last_used_at) : "Never"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={API_KEY_STATE[state]} />
                </TableCell>
                <TableCell className="text-right">
                  {state === "active" && <RevokeApiKeyButton apiKey={apiKey} />}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      <LoadMoreButton
        hasNextPage={apiKeys.hasNextPage}
        isFetchingNextPage={apiKeys.isFetchingNextPage}
        onLoadMore={() => void apiKeys.fetchNextPage()}
      />
    </div>
  );
}

export function ApiKeysCard() {
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null);
  return (
    <Card id="api-keys" className="scroll-mt-20">
      <CardHeader>
        <CardTitle>API keys</CardTitle>
        <CardDescription>
          The SDK and the replay worker use a project key. Give each agent or machine its own.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <CreateApiKeyForm onCreated={setCreatedKey} />
        <ApiKeyList />
      </CardContent>
      <ApiKeySecretDialog createdKey={createdKey} onClose={() => setCreatedKey(null)} />
    </Card>
  );
}
