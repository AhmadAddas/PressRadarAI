"use client";

import Link from "next/link";

import { SignOutButton } from "@/components/signout-button";

type AccountMenuProps = {
  name: string;
  email: string;
};

export function AccountMenu({ name, email }: Readonly<AccountMenuProps>) {
  return (
    <details className="account-menu">
      <summary aria-label={`Open account menu for ${name}`}>
        <span className="avatar" aria-hidden="true">
          {initials(name)}
        </span>
        <span className="account-name">{name}</span>
      </summary>
      <div className="account-popover">
        <div className="account-identity">
          <strong>{name}</strong>
          <span>{email}</span>
        </div>
        <Link className="button button-secondary" href="/app/profile">
          View profile
        </Link>
        <SignOutButton />
      </div>
    </details>
  );
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}
