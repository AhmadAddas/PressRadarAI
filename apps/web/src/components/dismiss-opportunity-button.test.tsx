import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DismissOpportunityButton } from "./dismiss-opportunity-button";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

describe("DismissOpportunityButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("dismisses the opportunity and refreshes the dashboard", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));
    render(<DismissOpportunityButton opportunityId="opportunity-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));

    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/opportunities/opportunity-1/status"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "dismissed" }),
      }),
    );
  });
});
