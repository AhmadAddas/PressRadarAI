import type { MediaItem } from "./media-types";

export type MediaFilter = "all" | "api" | "rss";

export function filterMedia(
  items: MediaItem[],
  filter: MediaFilter,
): MediaItem[] {
  if (filter === "rss") {
    return items.filter((item) => item.source_type === "rss");
  }
  if (filter === "api") {
    return items.filter((item) => item.source_type === "news");
  }
  return items;
}
