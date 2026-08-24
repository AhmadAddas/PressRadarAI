import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountMenu } from "./account-menu";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("AccountMenu", () => {
  it("shows identity details and account actions", () => {
    render(<AccountMenu name="Amina Rahman" email="amina@example.com" />);

    const menu = screen.getByLabelText("Open account menu for Amina Rahman");
    expect(menu).toHaveTextContent("ARAmina Rahman");
    expect(screen.getByText("amina@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View profile" })).toHaveAttribute(
      "href",
      "/app/profile",
    );
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("closes when the user presses outside the menu", () => {
    render(<AccountMenu name="Amina Rahman" email="amina@example.com" />);

    const summary = screen.getByLabelText("Open account menu for Amina Rahman");
    const details = summary.closest("details");
    fireEvent.click(summary);
    expect(details).toHaveAttribute("open");

    fireEvent.pointerDown(document.body);
    expect(details).not.toHaveAttribute("open");
  });
});
