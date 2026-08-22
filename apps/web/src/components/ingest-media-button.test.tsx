import { fireEvent, render, screen } from "@testing-library/react";
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

    fireEvent.click(
      screen.getByRole("button", { name: "Ingest simulated media" }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Added 3 media items.",
    );
    expect(refresh).toHaveBeenCalledOnce();
  });
});
