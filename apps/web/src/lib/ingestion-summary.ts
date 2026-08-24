export type IngestionCounts = {
  created: number;
  restored: number;
  duplicates: number;
};

export function ingestionSummary(counts: IngestionCounts): string {
  const messages: string[] = [];
  if (counts.created) messages.push(`Added ${counts.created} media items.`);
  if (counts.restored) {
    messages.push(
      `Restored ${counts.restored} previously deleted media items.`,
    );
  }
  if (counts.duplicates) {
    messages.push(
      counts.duplicates === 1
        ? "1 media item was already ingested."
        : `${counts.duplicates} media items were already ingested.`,
    );
  }
  return messages.join(" ") || "No media items were available to ingest.";
}
