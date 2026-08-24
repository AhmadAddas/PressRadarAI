import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { languageEvent } from "./language-menu";
import { PageTranslator } from "./page-translator";

vi.mock("next/navigation", () => ({ usePathname: () => "/app" }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("PageTranslator", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
    vi.restoreAllMocks();
  });

  it("uses Local AI for Arabic, applies RTL, and restores original English", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ translations: ["لوحة الفرص"] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(
      <PageTranslator>
        <h1>Opportunity dashboard</h1>
      </PageTranslator>,
    );

    act(() => {
      window.dispatchEvent(new CustomEvent(languageEvent, { detail: "ar" }));
    });
    await waitFor(() => expect(screen.getByText("لوحة الفرص")).toBeVisible());
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    expect(request).toHaveBeenCalledOnce();
    expect(JSON.parse(String(request.mock.calls[0]?.[1]?.body))).toEqual({
      language_code: "ar",
      language_name: "Arabic",
      texts: ["Opportunity dashboard"],
    });

    act(() => {
      window.dispatchEvent(new CustomEvent(languageEvent, { detail: "en" }));
    });
    expect(screen.getByText("Opportunity dashboard")).toBeVisible();
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
    expect(request).toHaveBeenCalledOnce();
  });
});
