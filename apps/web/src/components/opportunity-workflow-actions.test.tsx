import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { OpportunityWorkflowActions } from "./opportunity-workflow-actions";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe("OpportunityWorkflowActions", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("requires an explicit approval action before presenting send", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    const { rerender } = render(
      <OpportunityWorkflowActions
        opportunityId="opportunity-1"
        status="ready"
        hasPitch
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve pitch" }));
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Pitch approved."),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/opportunities/opportunity-1/approve"),
      expect.objectContaining({ method: "POST" }),
    );

    rerender(
      <OpportunityWorkflowActions
        opportunityId="opportunity-1"
        status="approved"
        hasPitch
      />,
    );
    expect(
      screen.getByRole("button", { name: "Send pitch" }),
    ).toBeInTheDocument();
  });
});
