import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { IngestMediaButton } from "./ingest-media-button";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

describe("IngestMediaButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("reports newly ingested media and refreshes the feed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 3, restored: 0, duplicates: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<IngestMediaButton />);

    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Added 3 media items."),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("reports duplicate media without shifting the action area", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 0, restored: 0, duplicates: 3 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<IngestMediaButton />);

    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "3 media items were already ingested.",
      ),
    );
  });

  it("reports restored media separately", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 0, restored: 2, duplicates: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<IngestMediaButton />);

    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Restored 2 previously deleted media items. 1 media item was already ingested.",
      ),
    );
  });

  it("keeps its label stable while ingestion is pending", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    render(<IngestMediaButton />);

    const button = screen.getByRole("button", {
      name: "Ingest simulated media",
    });
    fireEvent.click(button);

    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveTextContent("Ingest simulated media");
  });
});
