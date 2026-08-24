"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { toast } from "sonner";

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
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
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
        toast.error("Unable to save the pitch draft.");
        return;
      }
      toast.success("Draft saved.");
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
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
          aria-busy={saving}
        >
          Save draft
        </button>
      </div>
    </div>
  );
}
