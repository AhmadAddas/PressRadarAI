import { describe, expect, it } from "vitest";

import { filterMedia } from "./media-filter";
import type { MediaItem } from "./media-types";

const items = [
  { id: "rss", source_type: "rss" },
  { id: "api", source_type: "news" },
] as MediaItem[];

describe("filterMedia", () => {
  it("removes RSS items from the API feed filter", () => {
    expect(filterMedia(items, "api").map((item) => item.id)).toEqual(["api"]);
  });

  it("shows only RSS items for the RSS feed filter", () => {
    expect(filterMedia(items, "rss").map((item) => item.id)).toEqual(["rss"]);
  });
});
