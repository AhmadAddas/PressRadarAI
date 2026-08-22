import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountMenu } from "./account-menu";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("AccountMenu", () => {
  it("shows identity details and account actions", () => {
    render(<AccountMenu name="Amina Rahman" email="amina@example.com" />);

    const menu = screen.getByLabelText("Open account menu for Amina Rahman");
    expect(menu.querySelector(".avatar")).toHaveTextContent("AR");
    expect(menu.querySelector(".account-trigger")).toHaveTextContent(
      "Amina Rahman",
    );
    expect(screen.getByText("amina@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View profile" })).toHaveAttribute(
      "href",
      "/app/profile",
    );
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });
});
