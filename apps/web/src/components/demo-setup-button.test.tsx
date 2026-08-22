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

    const toggle = screen.getByRole("button", {
      name: "Load demo workspace",
    });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(toggle);

    const loadedToggle = await screen.findByRole("button", {
      name: "Demo workspace loaded",
    });
    expect(loadedToggle).toHaveAttribute("aria-pressed", "true");
    expect(loadedToggle).toBeDisabled();
    expect(
      screen.queryByText(/Demo workspace is already ready/i),
    ).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/demo/setup"),
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("renders a ready workspace without flashing the unloaded state", () => {
    render(<DemoSetupButton initiallyReady />);

    const toggle = screen.getByRole("button", {
      name: "Demo workspace loaded",
    });
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(toggle).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Load demo workspace" }),
    ).not.toBeInTheDocument();
  });
});
