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

  async function load() {
    setError("");
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/audit`,
        { credentials: "include" },
      );
      if (!response.ok) {
        setError("Unable to load history.");
        return;
      }
      setEvents((await response.json()) as AuditEvent[]);
    } catch {
      setError("PressRadar is temporarily unavailable.");
    }
  }

  return (
    <div className="audit-trail">
      <button type="button" onClick={load} disabled={events !== null}>
        {events === null ? "Show history" : "History loaded"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {events ? (
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
  );
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
