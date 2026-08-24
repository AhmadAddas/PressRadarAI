export type LicenseDetails = {
  name: string;
  summary: string;
  source_url: string | null;
  known: boolean;
};

export type LocalAIStatus = {
  enabled: boolean;
  reachable: boolean;
  model: string;
  license: LicenseDetails;
  recommended_model: string;
  recommendation: string;
};
