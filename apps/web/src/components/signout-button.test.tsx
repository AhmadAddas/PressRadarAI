import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SignOutButton } from "./signout-button";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
}));

describe("SignOutButton", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
  });

  it("exposes its busy state while signing out", async () => {
    let finishRequest: ((response: Response) => void) | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          finishRequest = resolve;
        }),
    );
    render(<SignOutButton />);

    const button = screen.getByRole("button", { name: "Sign out" });
    fireEvent.click(button);

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");

    finishRequest?.(new Response(null, { status: 204 }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signin"));
  });
});
