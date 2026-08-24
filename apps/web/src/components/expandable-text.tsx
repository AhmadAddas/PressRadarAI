"use client";

import { useState } from "react";

export function ExpandableText({
  text,
  threshold = 180,
}: Readonly<{ text: string; threshold?: number }>) {
  const [expanded, setExpanded] = useState(false);
  const canExpand = text.length > threshold;

  return (
    <div className="expandable-text">
      <p className={canExpand && !expanded ? "text-clamped" : undefined}>
        {text}
      </p>
      {canExpand ? (
        <button
          className="text-action"
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          {expanded ? "See less" : "See more"}
        </button>
      ) : null}
    </div>
  );
}
