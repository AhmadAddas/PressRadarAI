"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import type { OpportunityStatus } from "@/lib/opportunity-types";

type WorkflowActionsProps = {
  opportunityId: string;
  status: OpportunityStatus;
  hasPitch: boolean;
};

export function OpportunityWorkflowActions({
  opportunityId,
  status,
  hasPitch,
}: WorkflowActionsProps) {
  const router = useRouter();
  const [working, setWorking] = useState(false);

  const action =
    status === "ready" && hasPitch
      ? "approve"
      : status === "approved"
        ? "send"
        : null;

  async function runAction() {
    if (!action) return;
    setWorking(true);
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/${action}`,
        { method: "POST", credentials: "include" },
      );
      if (!response.ok) {
        toast.error(
          action === "approve"
            ? "Unable to approve this pitch."
            : "Delivery failed. The approved pitch can be retried.",
        );
        startTransition(() => router.refresh());
        return;
      }
      toast.success(action === "approve" ? "Pitch approved." : "Pitch sent.");
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  if (!action && status !== "sending") return null;

  return (
    <div className={`workflow-action workflow-action-${action ?? "pending"}`}>
      <button
        type="button"
        onClick={runAction}
        disabled={working || status === "sending"}
        aria-busy={working || status === "sending"}
      >
        {action === "approve" ? "Approve pitch" : "Send pitch"}
      </button>
    </div>
  );
}
