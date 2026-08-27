import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthForm } from "./auth-form";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

describe("AuthForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    push.mockReset();
    refresh.mockReset();
  });

  it("submits signup credentials and enters the protected application", async () => {
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (url) =>
        String(url).endsWith("/auth/signup")
          ? new Response(JSON.stringify({ user_id: "user-1" }), {
              status: 201,
              headers: { "Content-Type": "application/json" },
            })
          : new Response(null, { status: 503 }),
      );
    render(<AuthForm mode="signup" />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Amina" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "amina@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secure-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/app"));
    expect(request).toHaveBeenCalledWith(
      "http://localhost:8000/auth/signup",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });

  it("shows safe API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid email or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<AuthForm mode="signin" />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "amina@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password",
    );
  });

  it("rejects a first name longer than 25 characters before submission", () => {
    const request = vi.spyOn(globalThis, "fetch");
    render(<AuthForm mode="signup" />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: `${"A".repeat(26)} Noor` },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "amina@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secure-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "First name must be 25 characters or fewer.",
    );
    expect(request).not.toHaveBeenCalledWith(
      expect.stringContaining("/auth/signup"),
      expect.anything(),
    );
  });

  it("verifies the emailed signup code before onboarding", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      if (String(url).endsWith("/auth/signup")) {
        return new Response(
          JSON.stringify({
            verification_required: true,
            user_id: "user-1",
            challenge_id: "challenge-id-with-enough-length",
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        );
      }
      if (String(url).endsWith("/auth/signup/verify")) {
        return new Response(JSON.stringify({ onboarding_completed: false }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(null, { status: 503 });
    });
    render(<AuthForm mode="signup" />);

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Amina" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "amina@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secure-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    const code = await screen.findByLabelText("Email verification code");
    expect(code).toHaveAttribute("autocomplete", "one-time-code");
    expect(code).toHaveAttribute("inputmode", "numeric");
    fireEvent.input(code, { target: { value: "12ab34" } });
    expect(code).toHaveValue("1234");
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify email" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/onboarding"));
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      "http://localhost:8000/auth/signup/verify",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          user_id: "user-1",
          challenge_id: "challenge-id-with-enough-length",
          code: "123456",
        }),
      }),
    );
  });
});
