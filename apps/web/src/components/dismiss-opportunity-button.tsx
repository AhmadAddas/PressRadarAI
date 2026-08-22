"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function DismissOpportunityButton({
  opportunityId,
}: {
  opportunityId: string;
}) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [disabled, setDisabled] = useState(false);

  async function dismiss() {
    setDisabled(true);
    setError("");
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/status`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "dismissed" }),
        },
      );
      if (!response.ok) {
        setError("Unable to dismiss opportunity.");
        return;
      }
      router.refresh();
    } catch {
      setError("PressRadar is temporarily unavailable.");
    } finally {
      setDisabled(false);
    }
  }

  return (
    <div className="opportunity-action">
      <button type="button" onClick={dismiss} disabled={disabled}>
        {disabled ? "Dismissing…" : "Dismiss"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}
