import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PaginatedSelectableList } from "./paginated-selectable-list";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const items = Array.from({ length: 6 }, (_, index) => ({
  id: `item-${index + 1}`,
  label: `Item ${index + 1}`,
  content: <span>Content {index + 1}</span>,
}));

describe("PaginatedSelectableList", () => {
  beforeEach(() => {
    refresh.mockReset();
    vi.restoreAllMocks();
  });

  afterEach(() => vi.useRealTimers());

  it("paginates records without duplicating them", () => {
    render(
      <PaginatedSelectableList
        items={items}
        noun="media item"
        endpoint="media"
        className="media-list"
      />,
    );

    expect(screen.getByText("Content 1")).toBeInTheDocument();
    expect(screen.queryByText("Content 6")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Content 6")).toBeInTheDocument();
    expect(screen.queryByText("Content 1")).not.toBeInTheDocument();
  });

  it.each([
    ["client", "clients", "client-list"],
    ["opportunity", "opportunities", "opportunity-list"],
  ])("paginates %s records", (noun, endpoint, className) => {
    render(
      <PaginatedSelectableList
        items={items}
        noun={noun}
        endpoint={endpoint}
        className={className}
      />,
    );

    expect(
      screen.getByRole("navigation", { name: `${noun} pagination` }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Content 6")).toBeVisible();
  });

  it("deduplicates selection and requires the timed delete confirmation", async () => {
    vi.useFakeTimers();
    const request = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    render(
      <PaginatedSelectableList
        items={items.slice(0, 2)}
        noun="client"
        endpoint="clients"
        className="client-list"
      />,
    );

    fireEvent.click(screen.getByLabelText("Select all pages"));
    fireEvent.click(
      screen.getByRole("button", { name: "Delete selected (2)" }),
    );
    expect(
      screen.getByRole("button", { name: "Confirm in 5s" }),
    ).toBeDisabled();

    for (let second = 0; second < 5; second += 1) {
      await act(async () => vi.advanceTimersByTime(1000));
    }
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(request).toHaveBeenCalledTimes(2);
    expect(new Set(request.mock.calls.map(([url]) => url)).size).toBe(2);
  });

  it("selects cards and Ctrl-selects the records in between", () => {
    render(
      <PaginatedSelectableList
        items={items}
        noun="media item"
        endpoint="media"
        className="media-list"
      />,
    );

    const first = screen.getByLabelText("Select Item 1");
    fireEvent.click(first);
    fireEvent.keyDown(first, { key: "Control" });
    fireEvent.click(screen.getByLabelText("Select Item 4"));
    fireEvent.keyUp(first, { key: "Control" });

    expect(
      screen.getByRole("button", { name: "Delete selected (4)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Tip: Ctrl-select chooses a range.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Delete Item 1" })).toBeVisible();
  });
});
