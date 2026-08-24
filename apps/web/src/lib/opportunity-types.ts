export type OpportunityStatus =
  | "new"
  | "analyzing"
  | "ready"
  | "approved"
  | "sending"
  | "sent"
  | "dismissed"
  | "failed";

export type Opportunity = {
  id: string;
  client_id: string;
  client_name: string;
  client_company: string;
  client_deleted: boolean;
  media_item_id: string;
  source: string;
  headline: string;
  media_deleted: boolean;
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
  delivery: {
    provider: string;
    reference: string;
    sent_at: string;
  } | null;
  send_error: string | null;
  status: OpportunityStatus;
  detected_at: string;
};
