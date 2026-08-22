import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IngestMediaButton } from "./ingest-media-button";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

describe("IngestMediaButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("reports newly ingested media and refreshes the feed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 3, duplicates: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<IngestMediaButton />);

    expect(screen.getByRole("status")).toBeEmptyDOMElement();

    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Added 3 media items.",
    );
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("reports duplicate media without shifting the action area", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 0, duplicates: 3 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<IngestMediaButton />);

    const status = screen.getByRole("status");
    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    await waitFor(() =>
      expect(status).toHaveTextContent("3 media items were already ingested."),
    );
  });
});
