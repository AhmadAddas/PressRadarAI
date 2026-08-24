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

    fireEvent.click(screen.getByLabelText("Select all"));
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
});
