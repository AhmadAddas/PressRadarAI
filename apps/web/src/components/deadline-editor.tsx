"use client";

import { FormEvent, startTransition, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AccessibleDialog } from "@/components/accessible-dialog";
import { publicApiUrl } from "@/lib/api";

export function DeadlineEditor({
  mediaItemId,
  deadline: initialDeadline,
}: Readonly<{
  mediaItemId: string;
  deadline: string | null;
}>) {
  const router = useRouter();
  const [deadline, setDeadline] = useState(initialDeadline);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(
      new FormData(event.currentTarget).get("deadline") ?? "",
    );
    const parsed = new Date(value);
    if (!value || Number.isNaN(parsed.getTime())) {
      toast.error("Enter a valid deadline and time.");
      return;
    }
    await update(parsed.toISOString());
  }

  async function update(nextDeadline: string | null) {
    setSaving(true);
    try {
      const response = await fetch(
        `${publicApiUrl}/media/${mediaItemId}/deadline`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ deadline: nextDeadline }),
        },
      );
      const payload = (await response.json().catch(() => null)) as {
        deadline?: string | null;
        detail?: string;
      } | null;
      if (!response.ok) {
        toast.error(payload?.detail ?? "Unable to update the deadline.");
        return;
      }
      setDeadline(payload?.deadline ?? null);
      setEditing(false);
      toast.success(nextDeadline ? "Deadline updated." : "Deadline removed.");
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <AccessibleDialog
        title={deadline ? "Adjust media deadline" : "Set media deadline"}
        description="Choose the journalist deadline in your local time."
        onClose={() => setEditing(false)}
      >
        <form className="deadline-form" onSubmit={save}>
          <label>
            Deadline in your local time
            <input
              name="deadline"
              type="datetime-local"
              required
              defaultValue={deadline ? localDateTime(deadline) : ""}
            />
          </label>
          <div className="deadline-actions">
            <button type="submit" disabled={saving} aria-busy={saving}>
              Save deadline
            </button>
            <button
              className="button-secondary"
              type="button"
              disabled={saving}
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
            {deadline ? (
              <button
                className="button-secondary"
                type="button"
                disabled={saving}
                onClick={() => update(null)}
              >
                Remove deadline
              </button>
            ) : null}
          </div>
        </form>
      </AccessibleDialog>
    );
  }

  return (
    <div className="deadline-editor">
      {deadline ? (
        <strong>Deadline {formatTime(deadline)}</strong>
      ) : (
        <span>No deadline supplied</span>
      )}
      <button
        className="button-secondary button-compact"
        type="button"
        onClick={() => setEditing(true)}
      >
        {deadline ? "Adjust deadline" : "Set deadline"}
      </button>
    </div>
  );
}

function localDateTime(value: string): string {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
