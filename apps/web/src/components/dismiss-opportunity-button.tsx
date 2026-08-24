"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";

export function DismissOpportunityButton({
  opportunityId,
}: {
  opportunityId: string;
}) {
  const router = useRouter();
  const [disabled, setDisabled] = useState(false);

  async function dismiss() {
    setDisabled(true);
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
        toast.error("Unable to dismiss opportunity.");
        return;
      }
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
    } finally {
      setDisabled(false);
    }
  }

  return (
    <div className="opportunity-action">
      <button
        type="button"
        onClick={dismiss}
        disabled={disabled}
        aria-busy={disabled}
      >
        Dismiss
      </button>
    </div>
  );
}
