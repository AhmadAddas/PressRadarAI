import { describe, expect, it } from "vitest";

import { statusLabels, urgencyLevel } from "./opportunity-presentation";

describe("opportunity presentation", () => {
  const now = new Date("2026-08-22T12:00:00Z");

  it("classifies deadline urgency at the documented boundaries", () => {
    expect(urgencyLevel(null, now)).toBe("none");
    expect(urgencyLevel("2026-08-22T11:59:00Z", now)).toBe("overdue");
    expect(urgencyLevel("2026-08-22T13:00:00Z", now)).toBe("critical");
    expect(urgencyLevel("2026-08-23T12:00:00Z", now)).toBe("upcoming");
    expect(urgencyLevel("2026-08-23T12:01:00Z", now)).toBe("none");
  });

  it("gives each workflow state a user-facing label", () => {
    expect(Object.keys(statusLabels)).toHaveLength(8);
    expect(statusLabels.ready).toBe("Ready for review");
    expect(statusLabels.failed).toBe("Needs attention");
  });
});
