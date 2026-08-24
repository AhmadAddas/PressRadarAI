import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { MediaSourceManager } from "./media-source-manager";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const sources = [
  {
    id: "rss-1",
    workspace_id: "prod",
    name: "UAE RSS",
    kind: "rss" as const,
    url: "https://example.com/feed.xml",
    provider: null,
  },
  {
    id: "api-1",
    workspace_id: "prod",
    name: "UAE NewsAPI",
    kind: "api" as const,
    url: null,
    provider: "newsapi",
  },
];

describe("MediaSourceManager", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("filters configured RSS and API sources", () => {
    render(<MediaSourceManager sources={sources} suggestions={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Media options" }));
    fireEvent.change(screen.getByLabelText("Filter sources"), {
      target: { value: "rss" },
    });

    expect(screen.getByText("UAE RSS")).toBeInTheDocument();
    expect(screen.queryByText("UAE NewsAPI")).not.toBeInTheDocument();
  });

  it("closes media options when the user presses outside", () => {
    render(<MediaSourceManager sources={sources} suggestions={[]} />);
    const toggle = screen.getByRole("button", { name: "Media options" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    fireEvent.pointerDown(document.body);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("ingests Prod media and deletes configured sources", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ created: 2, duplicates: 0 }), {
          status: 200,
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<MediaSourceManager sources={sources} suggestions={[]} />);

    fireEvent.click(screen.getByRole("button", { name: "Ingest media" }));
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Added 2 media items."),
    );
    fireEvent.click(screen.getByRole("button", { name: "Media options" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/media/sources/rss-1"),
      expect.objectContaining({ method: "DELETE", credentials: "include" }),
    );
  });
});
