import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { MediaSourceManager } from "./media-source-manager";

const refresh = vi.fn();

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/media",
  useRouter: () => ({ refresh, replace }),
}));
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(() => 1),
    dismiss: vi.fn(),
  },
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
    replace.mockReset();
  });

  it("filters configured RSS and API sources", () => {
    render(<MediaSourceManager sources={sources} suggestions={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Media options" }));
    fireEvent.change(screen.getByLabelText("Filter sources"), {
      target: { value: "rss" },
    });

    expect(screen.getByText("UAE RSS")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Pagination appears when there are more than 5 items.",
      ),
    ).toHaveLength(2);
    expect(screen.queryByText("UAE NewsAPI")).not.toBeInTheDocument();
    expect(replace).toHaveBeenCalledWith("/app/media?source=rss", {
      scroll: false,
    });
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
        new Response(
          JSON.stringify({ created: 2, restored: 0, duplicates: 0 }),
          {
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<MediaSourceManager sources={sources} suggestions={[]} />);

    expect(
      screen.queryByRole("button", { name: "Ingest media" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Media options" }));
    const addRss = screen.getByRole("button", { name: "Add RSS source" });
    const ingest = screen.getByRole("button", { name: "Ingest media" });
    expect(addRss).toHaveClass("button-secondary");
    expect(
      addRss.compareDocumentPosition(ingest) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    fireEvent.click(ingest);
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Added 2 media items."),
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    const confirmation = screen.getByRole("alertdialog");
    expect(confirmation).toHaveTextContent("Delete UAE RSS?");
    expect(confirmation.parentElement).toHaveClass("modal-backdrop");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Delete source" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/media/sources/rss-1"),
      expect.objectContaining({ method: "DELETE", credentials: "include" }),
    );
  });
});
