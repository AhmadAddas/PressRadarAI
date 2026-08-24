"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import { SignOutButton } from "@/components/signout-button";

type AccountMenuProps = {
  name: string;
  email: string;
};

export function AccountMenu({ name, email }: Readonly<AccountMenuProps>) {
  const menuRef = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    function dismiss(event: PointerEvent | KeyboardEvent) {
      const menu = menuRef.current;
      if (!menu?.open) return;
      if (
        event.type === "keydown" &&
        (event as KeyboardEvent).key === "Escape"
      ) {
        menu.removeAttribute("open");
        menu.querySelector("summary")?.focus();
        return;
      }
      if (
        event.type === "pointerdown" &&
        !menu.contains(event.target as Node)
      ) {
        menu.removeAttribute("open");
      }
    }

    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", dismiss);
    };
  }, []);

  return (
    <details className="account-menu" ref={menuRef}>
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
