import { describe, expect, it } from "vitest";

import { formatSourceType } from "./media-presentation";

describe("formatSourceType", () => {
  it("preserves RSS as an uppercase acronym", () => {
    expect(formatSourceType("rss")).toBe("RSS");
    expect(formatSourceType("journalist_request")).toBe("Journalist Request");
  });
});
