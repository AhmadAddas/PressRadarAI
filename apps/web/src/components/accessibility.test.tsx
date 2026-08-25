import axe from "axe-core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccessibleDialog } from "@/components/accessible-dialog";
import { AccountMenu } from "@/components/account-menu";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/signout-button", () => ({
  SignOutButton: () => <button type="button">Sign out</button>,
}));

const axeOptions = {
  rules: {
    // JSDOM has no layout or canvas, so color contrast is covered manually.
    "color-contrast": { enabled: false },
  },
};

describe("shared accessibility foundations", () => {
  it("keeps the account navigation free of detectable accessibility violations", async () => {
    const { container } = render(
      <main id="main-content">
        <h1>Opportunity dashboard</h1>
        <nav aria-label="Account navigation">
          <AccountMenu name="Ahmad Example" email="ahmad@example.com" />
        </nav>
      </main>,
    );

    expect((await axe.run(container, axeOptions)).violations).toEqual([]);
  });

  it("labels, focuses, traps, and dismisses confirmation dialogs", async () => {
    const onClose = vi.fn();
    const { container } = render(
      <AccessibleDialog
        title="Delete client?"
        description="This action removes the selected client."
        onClose={onClose}
      >
        <button type="button">Delete</button>
        <button type="button">Cancel</button>
      </AccessibleDialog>,
    );

    const dialog = screen.getByRole("alertdialog", { name: "Delete client?" });
    const deleteButton = screen.getByRole("button", { name: "Delete" });
    const cancelButton = screen.getByRole("button", { name: "Cancel" });

    expect(deleteButton).toHaveFocus();
    cancelButton.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(deleteButton).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
    expect(dialog).toHaveAttribute("aria-describedby");
    expect((await axe.run(container, axeOptions)).violations).toEqual([]);
  });
});
