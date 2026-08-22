import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClientForm } from "./client-form";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

describe("ClientForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    push.mockReset();
    refresh.mockReset();
  });

  it("creates a client with simple monitoring rules", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "client-1" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<ClientForm />);

    fireEvent.change(screen.getByLabelText("Client name"), {
      target: { value: "Dr. Amina Noor" },
    });
    fireEvent.change(screen.getByLabelText("Company"), {
      target: { value: "Nexa AI" },
    });
    fireEvent.change(screen.getByLabelText("Keywords (comma separated)"), {
      target: { value: "Nexa AI, AI regulation" },
    });
    fireEvent.change(
      screen.getByLabelText("Monitoring rules (one phrase per line)"),
      {
        target: { value: "Dubai AI startup\nUAE AI regulation" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: "Create client" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/app/clients/client-1"),
    );
    const options = request.mock.calls[0]?.[1];
    expect(options).toEqual(
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(JSON.parse(String(options?.body))).toEqual(
      expect.objectContaining({
        keywords: ["Nexa AI", "AI regulation"],
        monitoring_rules: ["Dubai AI startup", "UAE AI regulation"],
      }),
    );
  });
});
