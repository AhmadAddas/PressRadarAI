export type OpportunityStatus =
  | "new"
  | "analyzing"
  | "ready"
  | "approved"
  | "sent"
  | "dismissed"
  | "failed";

export type Opportunity = {
  id: string;
  client_id: string;
  client_name: string;
  client_company: string;
  media_item_id: string;
  source: string;
  headline: string;
  journalist: string | null;
  published_at: string;
  deadline: string | null;
  matched_topics: string[];
  relevance_score: number | null;
  relevance_reason: string | null;
  analysis_error: string | null;
  pitch: {
    id: string;
    opportunity_id: string;
    content: string;
    generated_at: string;
    updated_at: string;
  } | null;
  pitch_error: string | null;
  status: OpportunityStatus;
  detected_at: string;
};
