import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DemoSetupButton } from "./demo-setup-button";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

describe("DemoSetupButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("prepares the demo workflow and refreshes the dashboard", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ opportunities_created: 3 }), {
        status: 200,
      }),
    );
    render(<DemoSetupButton />);

    fireEvent.click(
      screen.getByRole("button", { name: "Load demo workspace" }),
    );

    expect(
      await screen.findByText("Demo ready with 3 opportunities."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/demo/setup"),
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });
});
