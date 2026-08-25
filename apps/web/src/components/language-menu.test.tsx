import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageMenu, languageEvent } from "./language-menu";

describe("LanguageMenu", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          active: true,
          translation_available: true,
          analysis_model: "qwen2.5:0.5b-instruct",
          translation_model: "translategemma:4b",
        }),
        { status: 200 },
      ),
    );
  });

  it("keeps English as default and selects Arabic with its UAE flag", async () => {
    const listener = vi.fn();
    window.addEventListener(languageEvent, listener);
    render(<LanguageMenu />);

    await waitFor(() => expect(fetch).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /English/ }));
    fireEvent.click(screen.getByRole("button", { name: /العربية · Arabic/ }));

    expect(localStorage.getItem("pressradar-language")).toBe("ar");
    expect(
      screen.getByRole("button", { name: /العربية · Arabic/ }),
    ).toHaveTextContent("🇦🇪");
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(languageEvent, listener);
  });

  it("searches the broad language list", () => {
    render(<LanguageMenu />);
    fireEvent.click(screen.getByRole("button", { name: /English/ }));
    fireEvent.change(screen.getByLabelText("Search languages"), {
      target: { value: "Japanese" },
    });

    expect(screen.getByRole("button", { name: /Japanese/ })).toHaveTextContent(
      "🇯🇵",
    );
    expect(
      screen.queryByRole("button", { name: /Arabic/ }),
    ).not.toBeInTheDocument();
  });

  it("disables non-English languages when translation Local AI is unavailable", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          active: false,
          translation_available: false,
          analysis_model: "qwen2.5:0.5b-instruct",
          translation_model: "translategemma:4b",
        }),
        { status: 200 },
      ),
    );
    render(<LanguageMenu />);

    fireEvent.click(screen.getByRole("button", { name: /English/ }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Arabic/ })).toBeDisabled(),
    );
    for (const button of screen.getAllByRole("button", { name: /English/ })) {
      expect(button).toBeEnabled();
    }
  });
});
