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
        clientEmail="press@example.com"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve pitch" }));
    expect(screen.getByRole("button", { name: "Approve pitch" })).toHaveClass(
      "button-success-secondary",
    );
    expect(
      screen.getByRole("button", { name: "Approve pitch" }).parentElement,
    ).toHaveClass("workflow-action-approve");
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
        clientEmail="press@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Send Pitch" }));
    expect(screen.getByRole("button", { name: "Email" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "SMS" })).toBeDisabled();
    expect(
      screen.getByText(/Simulated delivery to press@example.com/),
    ).toBeVisible();
    expect(screen.getByText(/configure Twilio API keys/)).toBeVisible();
  });
});
