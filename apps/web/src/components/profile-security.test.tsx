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
});
