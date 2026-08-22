"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function IngestMediaButton() {
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [disabled, setDisabled] = useState(false);

  async function ingest() {
    setDisabled(true);
    setStatus("");
    try {
      const response = await fetch(`${publicApiUrl}/media/ingest`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        setStatus("Unable to ingest simulated media.");
        return;
      }
      const result = (await response.json()) as {
        created: number;
        duplicates: number;
      };
      setStatus(
        result.created
          ? `Added ${result.created} media items.`
          : `${result.duplicates} media items were already ingested.`,
      );
      router.refresh();
    } catch {
      setStatus("PressRadar is temporarily unavailable.");
    } finally {
      setDisabled(false);
    }
  }

  return (
    <div className="ingest-action">
      <button type="button" onClick={ingest} disabled={disabled}>
        {disabled ? "Ingesting…" : "Ingest simulated media"}
      </button>
      {status ? <p role="status">{status}</p> : null}
    </div>
  );
}
