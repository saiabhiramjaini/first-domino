import type { InfiniteData } from "@tanstack/react-query";

type Page<T> = { items: T[]; next_cursor: string | null };

export const FIRST_PAGE_CURSOR: string | null = null;

export function nextPageCursor<T>(page: Page<T>): string | null | undefined {
  return page.next_cursor ?? undefined;
}

export function pageItems<T>(data: InfiniteData<Page<T>> | undefined): T[] {
  return data?.pages.flatMap((page) => page.items) ?? [];
}
