import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { DeadlineEditor } from "./deadline-editor";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe("DeadlineEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("sets a missing deadline and refreshes related opportunities", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ deadline: "2026-08-27T10:30:00Z" }), {
        status: 200,
      }),
    );
    render(<DeadlineEditor mediaItemId="media-1" deadline={null} />);

    expect(screen.getByText("No deadline supplied")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Set deadline" }));
    fireEvent.change(screen.getByLabelText("Deadline in your local time"), {
      target: { value: "2026-08-27T14:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save deadline" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/media/media-1/deadline"),
      expect.objectContaining({ method: "PATCH", credentials: "include" }),
    );
    expect(toast.success).toHaveBeenCalledWith("Deadline updated.");
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("allows an existing deadline to be removed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ deadline: null }), { status: 200 }),
    );
    render(
      <DeadlineEditor mediaItemId="media-1" deadline="2026-08-27T10:30:00Z" />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Adjust deadline" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove deadline" }));

    await waitFor(() =>
      expect(screen.getByText("No deadline supplied")).toBeInTheDocument(),
    );
    expect(toast.success).toHaveBeenCalledWith("Deadline removed.");
  });
});
