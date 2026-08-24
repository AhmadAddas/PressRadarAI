"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import {
  ingestionSummary,
  type IngestionCounts,
} from "@/lib/ingestion-summary";

export function IngestMediaButton() {
  const router = useRouter();
  const [disabled, setDisabled] = useState(false);

  async function ingest() {
    setDisabled(true);
    try {
      const response = await fetch(`${publicApiUrl}/media/ingest`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        toast.error("Unable to ingest simulated media.");
        return;
      }
      const result = (await response.json()) as IngestionCounts;
      toast.success(ingestionSummary(result));
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
    } finally {
      setDisabled(false);
    }
  }

  return (
    <div className="ingest-action">
      <button
        type="button"
        onClick={ingest}
        disabled={disabled}
        aria-busy={disabled}
      >
        Ingest simulated media
      </button>
    </div>
  );
}
