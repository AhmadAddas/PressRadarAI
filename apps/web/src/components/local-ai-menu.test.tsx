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
  installed_models: ["llama3.2:3b"],
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
    expect(screen.getByRole("combobox", { name: "Ollama model" })).toHaveValue(
      "llama3.2:3b",
    );
    fireEvent.pointerDown(document.body);
    expect(screen.queryByText("Active local AI")).not.toBeInTheDocument();
  });

  it("hides the active model license when Local AI is inactive", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ...status,
          enabled: false,
          model_available: false,
          installed_models: [],
        }),
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
      screen.queryByRole("combobox", { name: "Ollama model" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/No Ollama models are installed yet/),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Deactivate Local AI" }),
    ).not.toBeInTheDocument();
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
          '{"completed":50,"total":100}\n{"status":"success","completed":100,"total":100}\n{"done":true}\n',
          {
            status: 200,
            headers: { "Content-Type": "application/x-ndjson" },
          },
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
    fireEvent.click(
      screen.getByRole("button", { name: "Clone another model" }),
    );
    fireEvent.submit(
      screen
        .getByRole("button", {
          name: "Check license to be able to clone",
        })
        .closest("form")!,
    );
    await act(async () => Promise.resolve());

    expect(
      screen.getByRole("button", { name: "Clone and activate in 5s" }),
    ).toBeDisabled();
    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    fireEvent.click(screen.getByRole("button", { name: "Clone and activate" }));
    await act(async () => Promise.resolve());

    expect(request.mock.calls).toContainEqual([
      expect.stringContaining("/local-ai/models/stream"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"activate":true'),
      }),
    ]);
    expect(toast.success).toHaveBeenCalledWith(
      "qwen2.5:0.5b-instruct is active.",
    );
  });

  it("can clone the selected model without activating it", async () => {
    vi.useFakeTimers();
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    const pullStream = new ReadableStream<Uint8Array>({
      start(controller) {
        streamController = controller;
      },
    });
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
        new Response(pullStream, {
          status: 200,
          headers: { "Content-Type": "application/x-ndjson" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...status, enabled: false }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    render(<LocalAIMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));
    await act(async () => Promise.resolve());
    fireEvent.click(
      screen.getByRole("button", { name: "Clone another model" }),
    );
    fireEvent.submit(
      screen
        .getByRole("button", {
          name: "Check license to be able to clone",
        })
        .closest("form")!,
    );
    await act(async () => Promise.resolve());
    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }

    fireEvent.click(screen.getByRole("button", { name: "Clone only" }));
    expect(
      screen.getByRole("progressbar", {
        name: "Downloading qwen2.5:0.5b-instruct",
      }),
    ).toBeVisible();
    await act(async () => {
      streamController.enqueue(
        new TextEncoder().encode('{"completed":50,"total":100}\n'),
      );
    });
    expect(screen.getByRole("progressbar")).toHaveValue(50);
    await act(async () => {
      streamController.enqueue(
        new TextEncoder().encode(
          '{"status":"success","completed":100,"total":100}\n{"done":true}\n',
        ),
      );
      streamController.close();
    });

    expect(request.mock.calls).toContainEqual([
      expect.stringContaining("/local-ai/models/stream"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"activate":false'),
      }),
    ]);
    expect(toast.success).toHaveBeenCalledWith(
      "qwen2.5:0.5b-instruct was cloned and remains inactive.",
    );
  });

  it("confirms before deleting an installed model", async () => {
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
            ...status,
            enabled: false,
            model_available: false,
            installed_models: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    render(<LocalAIMenu />);
    fireEvent.click(screen.getByRole("button", { name: "Local AI" }));
    await screen.findByText("Active local AI");

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Delete llama3.2:3b?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete model" }));

    await act(async () => Promise.resolve());
    expect(request).toHaveBeenLastCalledWith(
      expect.stringContaining("/local-ai/models?model=llama3.2%3A3b"),
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(toast.success).toHaveBeenCalledWith("llama3.2:3b was deleted.");
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
      screen
        .getByRole("button", {
          name: "Check license to be able to clone",
        })
        .closest("form")!,
    );

    expect(
      await screen.findByText(
        /Search the internet for the publisher's full model license/,
      ),
    ).toBeVisible();
  });
});
