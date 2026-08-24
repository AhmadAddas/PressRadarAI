import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { LocalAIMenu } from "./local-ai-menu";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const status = {
  enabled: true,
  reachable: true,
  model_available: true,
  model: "llama3.2:3b",
  license: {
    name: "llama3.2",
    summary: "Community license summary.",
    source_url: "https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct",
    known: true,
  },
  recommended_model: "qwen2.5:0.5b-instruct",
  recommendation: "A small model for a low-power VPS.",
};

describe("LocalAIMenu", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.useRealTimers());

  it("shows active model details and closes when clicking elsewhere", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(status), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<LocalAIMenu />);

    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));
    expect(await screen.findByText("Active local AI")).toBeVisible();
    expect(screen.getByText("llama3.2")).toBeVisible();
    fireEvent.pointerDown(document.body);
    expect(screen.queryByText("Active local AI")).not.toBeInTheDocument();
  });

  it("hides the active model license when Local AI is inactive", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ ...status, enabled: false, model_available: false }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    render(<LocalAIMenu />);

    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));

    expect(await screen.findByText("Local AI inactive")).toBeVisible();
    expect(
      screen.getByText("Clone an Ollama model to activate Local AI."),
    ).toBeVisible();
    expect(screen.queryByText("llama3.2:3b")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Activate Local AI" }),
    ).toBeDisabled();
    expect(screen.queryByText("Active model license")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Community license summary."),
    ).not.toBeInTheDocument();
  });

  it("requires license review and a timeout before cloning", async () => {
    vi.useFakeTimers();
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(status), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            name: "apache-2.0",
            summary: "Permits commercial use with notice obligations.",
            source_url: "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct",
            known: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...status, model: "qwen2.5:0.5b-instruct" }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    render(<LocalAIMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));
    await act(async () => Promise.resolve());
    expect(screen.getByText("Active local AI")).toBeVisible();
    fireEvent.submit(
      screen.getByRole("button", { name: "Check license" }).closest("form")!,
    );
    await act(async () => Promise.resolve());

    expect(screen.getByRole("button", { name: "Clone in 5s" })).toBeDisabled();
    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    fireEvent.click(screen.getByRole("button", { name: "Clone and activate" }));
    await act(async () => Promise.resolve());

    expect(request).toHaveBeenLastCalledWith(
      expect.stringContaining("/local-ai/models"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(toast.success).toHaveBeenCalledWith(
      "qwen2.5:0.5b-instruct is active.",
    );
  });

  it("offers an internet-search recommendation for an unknown license", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(status), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            name: "Unknown",
            summary: "No recognized license summary is available.",
            source_url: null,
            known: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    render(<LocalAIMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));
    await screen.findByText("Active local AI");
    fireEvent.submit(
      screen.getByRole("button", { name: "Check license" }).closest("form")!,
    );

    expect(
      await screen.findByText(
        /Search the internet for the publisher's full model license/,
      ),
    ).toBeVisible();
  });
});
