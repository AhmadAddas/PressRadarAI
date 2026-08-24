import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  afterEach(() => vi.useRealTimers());

  it("creates a client with simple monitoring rules", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "client-1" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<ClientForm />);

    fireEvent.change(screen.getByLabelText("Client name"), {
      target: { value: "dr. Amina Noor" },
    });
    fireEvent.change(screen.getByLabelText("Company"), {
      target: { value: "Nexa AI" },
    });
    fireEvent.change(screen.getByLabelText("Website"), {
      target: { value: "nexa.example.com" },
    });
    fireEvent.blur(screen.getByLabelText("Website"));
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "press@nexa.example.com" },
    });
    fireEvent.change(screen.getByLabelText("Phone number"), {
      target: { value: "+971501234567" },
    });
    fireEvent.change(screen.getByLabelText("Expertise (comma separated)"), {
      target: { value: "AI governance" },
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

    await waitFor(() => expect(push).toHaveBeenCalledWith("/app"));
    const options = request.mock.calls[0]?.[1];
    expect(options).toEqual(
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(JSON.parse(String(options?.body))).toEqual(
      expect.objectContaining({
        name: "Dr. Amina Noor",
        keywords: ["Nexa AI", "AI regulation"],
        website: "https://nexa.example.com",
        email: "press@nexa.example.com",
        phone: "+971501234567",
        monitoring_rules: ["Dubai AI startup", "UAE AI regulation"],
      }),
    );
  });

  it("warns with a timeout before creating an incomplete client", async () => {
    vi.useFakeTimers();
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "client-2" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<ClientForm />);
    fireEvent.change(screen.getByLabelText("Client name"), {
      target: { value: "Amina Noor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create client" }));

    expect(request).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Company, Website, Email, Phone number, Expertise and Monitoring rules will be empty",
    );
    expect(
      screen.getByRole("button", { name: "Confirm in 5s" }),
    ).toBeDisabled();

    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    fireEvent.click(screen.getByRole("button", { name: "Create anyway" }));
    await act(async () => Promise.resolve());

    expect(request).toHaveBeenCalledOnce();
  });

  it("warns before saving an incomplete edit and returns to the dashboard", async () => {
    vi.useFakeTimers();
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "client-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(
      <ClientForm
        client={{
          id: "client-1",
          workspace_id: "workspace-1",
          name: "Amina Noor",
          company: "",
          website: null,
          email: null,
          phone: null,
          industry: null,
          description: null,
          location: null,
          expertise: [],
          spokesperson_name: null,
          spokesperson_title: null,
          keywords: [],
          excluded_keywords: [],
          preferred_topics: [],
          tone: null,
          monitoring_rules: [],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(request).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Save this client with incomplete context?",
    );

    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    fireEvent.click(screen.getByRole("button", { name: "Save anyway" }));
    await act(async () => Promise.resolve());

    expect(request).toHaveBeenCalledWith(
      expect.stringMatching(/\/clients\/client-1$/),
      expect.objectContaining({ method: "PUT" }),
    );
    expect(push).toHaveBeenCalledWith("/app");
  });

  it("presents cancel as a secondary action", () => {
    render(<ClientForm />);

    expect(screen.getByRole("link", { name: "Cancel" })).toHaveAttribute(
      "class",
      expect.stringContaining("button-secondary"),
    );
  });

  it("requires a website with a valid domain name", () => {
    render(<ClientForm />);
    const website = screen.getByLabelText("Website");

    fireEvent.change(website, { target: { value: "https://localhost" } });

    expect(website).toBeInvalid();
  });
});
