import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TOTPOnboarding } from "./totp-onboarding";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }) }));
vi.mock("qrcode", () => ({
  default: { toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,qr") },
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

describe("TOTPOnboarding", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      if (String(url).endsWith("/auth/2fa/setup")) {
        return new Response(
          JSON.stringify({
            secret: "MANUALKEY123",
            provisioning_uri: "otpauth://setup",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(null, { status: 204 });
    });
  });

  afterEach(() => vi.useRealTimers());

  it("shows QR and manual key and delays the warned skip action", async () => {
    render(<TOTPOnboarding />);

    expect(await screen.findByText("MANUALKEY123")).toBeVisible();
    expect(await screen.findByAltText("TOTP setup QR code")).toBeVisible();
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    expect(screen.getByRole("button", { name: "Skip in 5s" })).toBeDisabled();
    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    fireEvent.click(screen.getByRole("button", { name: "Skip 2FA" }));
    await act(async () => Promise.resolve());
    expect(replace).toHaveBeenCalledWith("/app");
  });
});
