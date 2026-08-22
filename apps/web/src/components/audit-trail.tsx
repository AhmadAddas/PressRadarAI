"use client";

import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

type AuditEvent = {
  id: string;
  action: string;
  occurred_at: string;
  detail: string | null;
};

export function AuditTrail({ opportunityId }: { opportunityId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    if (events !== null) {
      setExpanded(true);
      return;
    }
    setError("");
    setExpanded(true);
    setLoading(true);
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/audit`,
        { credentials: "include" },
      );
      if (!response.ok) {
        setError("Unable to load history.");
        setExpanded(false);
        return;
      }
      setEvents((await response.json()) as AuditEvent[]);
    } catch {
      setError("PressRadar is temporarily unavailable.");
      setExpanded(false);
    } finally {
      setLoading(false);
    }
  }

  const panelId = `audit-${opportunityId}`;
  return (
    <div className="audit-trail">
      <button
        className="button-secondary audit-toggle"
        type="button"
        onClick={toggle}
        disabled={loading}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        {expanded ? "Hide history" : "Show history"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {expanded ? (
        <div className="audit-panel" id={panelId}>
          {loading ? <p role="status">Loading history…</p> : null}
          {events && !loading ? (
            <ol>
              {events.map((event) => (
                <li key={event.id}>
                  <span>{event.action.replaceAll("_", " ")}</span>
                  <time dateTime={event.occurred_at}>
                    {formatTime(event.occurred_at)}
                  </time>
                  {event.detail ? <small>{event.detail}</small> : null}
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
