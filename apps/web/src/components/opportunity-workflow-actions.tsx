"use client";

import { useRouter } from "next/navigation";
import { startTransition, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import type { OpportunityStatus } from "@/lib/opportunity-types";

type WorkflowActionsProps = {
  opportunityId: string;
  status: OpportunityStatus;
  hasPitch: boolean;
  clientEmail?: string | null;
};

export function OpportunityWorkflowActions({
  opportunityId,
  status,
  hasPitch,
  clientEmail,
}: WorkflowActionsProps) {
  const router = useRouter();
  const [working, setWorking] = useState(false);
  const [sendOpen, setSendOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sendOpen) return;
    const close = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setSendOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [sendOpen]);

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

  if (action === "send") {
    return (
      <div className="workflow-action workflow-action-send" ref={menuRef}>
        <button
          className="button-success"
          type="button"
          onClick={() => setSendOpen((current) => !current)}
          aria-expanded={sendOpen}
        >
          Send Pitch
        </button>
        {sendOpen ? (
          <div className="send-pitch-menu">
            <button
              className="button-success"
              type="button"
              onClick={runAction}
              disabled={working || !clientEmail}
            >
              Email
            </button>
            <small>
              {clientEmail
                ? `Simulated delivery to ${clientEmail}.`
                : "Add a client email to send."}
            </small>
            <button
              className="button-secondary is-blocked"
              type="button"
              disabled
            >
              SMS
            </button>
            <small>
              Unavailable: configure Twilio API keys and phone numbers to enable
              SMS.
            </small>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className={`workflow-action workflow-action-${action ?? "pending"}`}>
      <button
        className="button-success-secondary"
        type="button"
        onClick={runAction}
        disabled={working || status === "sending"}
        aria-busy={working || status === "sending"}
      >
        {action === "approve" ? "Approve pitch" : "Send Pitch"}
      </button>
    </div>
  );
}
