import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("identifies the application and its purpose", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        name: "Turn media opportunities into timely pitches.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Create account" }),
    ).toHaveAttribute("href", "/signup");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveClass(
      "button",
      "button-secondary",
    );
  });
});
