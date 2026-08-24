export function formatSourceType(value: string): string {
  return value
    .split("_")
    .map((part) =>
      part.toLowerCase() === "rss"
        ? "RSS"
        : `${part.charAt(0).toUpperCase()}${part.slice(1)}`,
    )
    .join(" ");
}
