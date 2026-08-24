"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";

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
      const result = (await response.json()) as {
        created: number;
        duplicates: number;
      };
      toast.success(
        result.created
          ? `Added ${result.created} media items.`
          : `${result.duplicates} media items were already ingested.`,
      );
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
