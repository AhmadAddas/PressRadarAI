import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { PitchEditor } from "./pitch-editor";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe("PitchEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("saves an edited draft and refreshes the dashboard", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    render(
      <PitchEditor
        opportunityId="opportunity-1"
        initialContent="Generated draft"
        generationError={null}
      />,
    );

    fireEvent.change(screen.getByLabelText("Pitch draft"), {
      target: { value: "Verified edited draft" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Draft saved."),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/opportunities/opportunity-1/pitch"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ content: "Verified edited draft" }),
      }),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });
});
