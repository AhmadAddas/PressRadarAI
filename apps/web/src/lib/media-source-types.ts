export type MediaSourceKind = "rss" | "api";

export type MediaSource = {
  id: string;
  workspace_id: string;
  name: string;
  kind: MediaSourceKind;
  url: string | null;
  provider: string | null;
};

export type MediaSourceSuggestion = Omit<MediaSource, "id" | "workspace_id">;
