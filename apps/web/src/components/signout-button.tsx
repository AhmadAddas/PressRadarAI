"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function SignOutButton() {
  const router = useRouter();
  const [disabled, setDisabled] = useState(false);

  async function signOut() {
    setDisabled(true);
    try {
      await fetch(`${publicApiUrl}/auth/signout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      router.replace("/signin");
      router.refresh();
    }
  }

  return (
    <button type="button" onClick={signOut} disabled={disabled}>
      Sign out
    </button>
  );
}
