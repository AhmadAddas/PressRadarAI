import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuditTrail } from "./audit-trail";

describe("AuditTrail", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and renders the opportunity history on demand", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "event-1",
            action: "pitch_approved",
            occurred_at: "2026-08-22T10:00:00Z",
            detail: null,
          },
        ]),
        { status: 200 },
      ),
    );
    render(<AuditTrail opportunityId="opportunity-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Show history" }));

    expect(await screen.findByText("pitch approved")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/opportunities/opportunity-1/audit"),
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
