export type LicenseDetails = {
  name: string;
  summary: string;
  source_url: string | null;
  known: boolean;
};

export type LocalAIStatus = {
  enabled: boolean;
  reachable: boolean;
  model_available: boolean;
  installed_models: string[];
  model: string;
  analysis_model: string;
  analysis_model_available: boolean;
  translation_model: string;
  translation_model_available: boolean;
  license: LicenseDetails;
  recommended_model: string;
  recommendation: string;
};

export type PublicLocalAIStatus = {
  active: boolean;
  translation_available: boolean;
  analysis_model: string;
  translation_model: string;
};
