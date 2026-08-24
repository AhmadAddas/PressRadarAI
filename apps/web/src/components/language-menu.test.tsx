import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageMenu, languageEvent } from "./language-menu";

describe("LanguageMenu", () => {
  beforeEach(() => localStorage.clear());

  it("keeps English as default and selects Arabic with its UAE flag", () => {
    const listener = vi.fn();
    window.addEventListener(languageEvent, listener);
    render(<LanguageMenu />);

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
});
