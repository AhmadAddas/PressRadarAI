import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileSecurity } from "./profile-security";

vi.mock("qrcode", () => ({ default: { toDataURL: vi.fn() } }));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

describe("ProfileSecurity", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("requires matching new passwords before submitting", () => {
    const request = vi.spyOn(globalThis, "fetch");
    render(<ProfileSecurity totpEnabled={false} />);

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "current-password" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-one" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-password-two" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "The new passwords do not match.",
    );
    expect(request).not.toHaveBeenCalled();
  });

  it("submits only matching password fields", async () => {
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    render(<ProfileSecurity totpEnabled={false} />);

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "current-password" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-value" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-password-value" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    await waitFor(() => expect(request).toHaveBeenCalledOnce());
    expect(request).toHaveBeenCalledWith(
      expect.stringContaining("/auth/password"),
      expect.objectContaining({
        body: JSON.stringify({
          current_password: "current-password",
          new_password: "new-password-value",
        }),
      }),
    );
  });

  it("explains and centers email verification before changing 2FA", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ challenge_id: "challenge-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<ProfileSecurity totpEnabled />);

    expect(
      screen.getByText(/requires a code sent to your verified email address/i),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Change 2FA" }));

    const firstDigit = await screen.findByLabelText(
      "Email verification code, digit 1",
    );
    expect(screen.getByText("ENGE-1")).toBeVisible();
    expect(firstDigit.closest("form")).toHaveClass(
      "profile-email-verification",
    );
  });

  it("shows progress and prevents duplicate 2FA email requests", async () => {
    let resolveRequest: ((response: Response) => void) | undefined;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveRequest = resolve;
        }),
    );
    render(<ProfileSecurity totpEnabled />);

    const changeButton = screen.getByRole("button", { name: "Change 2FA" });
    fireEvent.click(changeButton);
    fireEvent.click(changeButton);

    expect(request).toHaveBeenCalledOnce();
    expect(
      screen.getByRole("button", { name: "Sending email code…" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Deactivate 2FA" }),
    ).toBeDisabled();

    resolveRequest?.(
      new Response(JSON.stringify({ challenge_id: "challenge-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await screen.findByLabelText("Email verification code, digit 1");
  });
});
