import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DemoSetupButton } from "./demo-setup-button";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

describe("DemoSetupButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("switches from Prod and prepares the isolated Demo workspace", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ opportunities_created: 3 }), {
        status: 200,
      }),
    );
    render(<DemoSetupButton workspaceKind="prod" />);

    const toggle = screen.getByRole("button", {
      name: "Switch to Demo workspace",
    });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining("/auth/workspace"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ workspace_kind: "demo" }),
        }),
      );
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining("/demo/setup"),
        expect.objectContaining({ method: "POST", credentials: "include" }),
      );
      expect(refresh).toHaveBeenCalledOnce();
    });
  });

  it("switches from Demo back to Prod without reseeding", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ workspace_kind: "prod" }), {
          status: 200,
        }),
      );
    render(<DemoSetupButton workspaceKind="demo" />);

    const toggle = screen.getByRole("button", {
      name: "Switch to Prod workspace",
    });
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(toggle);

    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/workspace"),
      expect.objectContaining({
        body: JSON.stringify({ workspace_kind: "prod" }),
      }),
    );
  });
});
