"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

type PitchEditorProps = {
  opportunityId: string;
  initialContent: string;
  generationError: string | null;
};

export function PitchEditor({
  opportunityId,
  initialContent,
  generationError,
}: PitchEditorProps) {
  const router = useRouter();
  const [content, setContent] = useState(initialContent);
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    setStatus("");
    try {
      const response = await fetch(
        `${publicApiUrl}/opportunities/${opportunityId}/pitch`,
        {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        },
      );
      if (!response.ok) {
        setStatus("Unable to save the pitch draft.");
        return;
      }
      setStatus("Draft saved.");
      router.refresh();
    } catch {
      setStatus("PressRadar is temporarily unavailable.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="pitch-editor">
      <label htmlFor={`pitch-${opportunityId}`}>Pitch draft</label>
      {generationError ? <p role="alert">{generationError}</p> : null}
      <textarea
        id={`pitch-${opportunityId}`}
        value={content}
        maxLength={3000}
        onChange={(event) => setContent(event.target.value)}
        placeholder="Write a verified expert commentary draft."
      />
      <div className="pitch-actions">
        <button
          type="button"
          onClick={save}
          disabled={saving || !content.trim()}
        >
          {saving ? "Saving…" : "Save draft"}
        </button>
        {status ? <p role="status">{status}</p> : null}
      </div>
    </div>
  );
}
