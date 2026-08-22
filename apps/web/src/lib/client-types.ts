export type Client = {
  id: string;
  workspace_id: string;
  name: string;
  company: string;
  website: string | null;
  industry: string | null;
  description: string | null;
  location: string | null;
  expertise: string[];
  spokesperson_name: string | null;
  spokesperson_title: string | null;
  keywords: string[];
  excluded_keywords: string[];
  preferred_topics: string[];
  tone: string | null;
  monitoring_rules: string[];
};
