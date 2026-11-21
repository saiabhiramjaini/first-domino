"use client";

import { Button } from "@/components/ui/button";

type LoadMoreButtonProps = {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
};

export function LoadMoreButton({
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
}: LoadMoreButtonProps) {
  if (!hasNextPage) return null;
  return (
    <div className="flex justify-center">
      <Button variant="outline" onClick={onLoadMore} disabled={isFetchingNextPage}>
        {isFetchingNextPage ? "Loading..." : "Load more"}
      </Button>
    </div>
  );
}
