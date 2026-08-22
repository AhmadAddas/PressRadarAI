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
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ user_id: "user-1" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
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
});
