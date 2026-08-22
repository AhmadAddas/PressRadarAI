import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("identifies the application and its purpose", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: "PressRadar" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Turn media opportunities into timely, relevant pitches.",
      ),
    ).toBeInTheDocument();
  });
});
