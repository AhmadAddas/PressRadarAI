import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ApplicationError from "./error";
import ApplicationLoading from "./loading";

describe("application route states", () => {
  it("announces dashboard loading", () => {
    render(<ApplicationLoading />);

    expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByRole("heading", { name: "Loading your workspace…" }),
    ).toBeInTheDocument();
  });

  it("offers a safe retry when the dashboard fails", () => {
    const reset = vi.fn();
    render(<ApplicationError reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(reset).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your data is unchanged",
    );
  });
});
