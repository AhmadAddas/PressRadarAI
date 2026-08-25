"use client";

import { useEffect, useState } from "react";

import { LanguageMenu } from "@/components/language-menu";
import { publicApiUrl } from "@/lib/api";
import type { PublicLocalAIStatus } from "@/lib/local-ai-types";

export function PublicAIControls() {
  const [status, setStatus] = useState<PublicLocalAIStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch(`${publicApiUrl}/local-ai/public-status`)
      .then(async (response) => {
        if (!response.ok) return;
        const result = (await response.json()) as PublicLocalAIStatus;
        if (!cancelled) setStatus(result);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="public-ai-controls" data-no-translate>
      <span className="public-ai-status" role="status">
        <span
          className={`status-dot ${status?.active ? "is-active" : ""}`}
          aria-hidden="true"
        />
        Local AI {status?.active ? "active" : "inactive"}
      </span>
      <LanguageMenu status={status} />
    </div>
  );
}
