"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

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
  const [message, setMessage] = useState("");
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
    setMessage("");
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/${action}`,
        { method: "POST", credentials: "include" },
      );
      if (!response.ok) {
        setMessage(
          action === "approve"
            ? "Unable to approve this pitch."
            : "Delivery failed. The approved pitch can be retried.",
        );
        router.refresh();
        return;
      }
      setMessage(action === "approve" ? "Pitch approved." : "Pitch sent.");
      router.refresh();
    } catch {
      setMessage("PressRadar is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  if (!action && status !== "sending") return null;

  return (
    <div className="workflow-action">
      <button
        type="button"
        onClick={runAction}
        disabled={working || status === "sending"}
      >
        {status === "sending"
          ? "Sending…"
          : working
            ? action === "approve"
              ? "Approving…"
              : "Sending…"
            : action === "approve"
              ? "Approve pitch"
              : "Send pitch"}
      </button>
      {message ? <p role="status">{message}</p> : null}
    </div>
  );
}
