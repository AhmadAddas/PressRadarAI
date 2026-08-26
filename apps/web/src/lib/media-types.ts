export type MediaItem = {
  id: string;
  source: string;
  source_type: "news" | "journalist_request" | "rss" | "social";
  author: string | null;
  journalist: string | null;
  headline: string;
  display_headline: string | null;
  body: string;
  url: string | null;
  published_at: string;
  deadline: string | null;
  topics: string[];
  external_id: string | null;
  ingested_at: string;
};
