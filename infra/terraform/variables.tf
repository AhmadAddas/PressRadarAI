variable "project_id" {
  description = "GCP project that owns the PressRadar deployment."
  type        = string
}

variable "region" {
  description = "Cloud Run, Artifact Registry, and BigQuery region."
  type        = string
  default     = "me-central1"
}

variable "api_image" {
  description = "Immutable API container image digest."
  type        = string
}

variable "web_image" {
  description = "Immutable web container image digest built with the public API URL."
  type        = string
}

variable "web_origin" {
  description = "Public HTTPS web origin allowed by API CORS and secure cookies."
  type        = string

  validation {
    condition     = startswith(var.web_origin, "https://")
    error_message = "web_origin must use HTTPS."
  }
}

variable "ollama_base_url" {
  description = "HTTPS endpoint for the production Ollama-compatible provider."
  type        = string

  validation {
    condition     = startswith(var.ollama_base_url, "https://")
    error_message = "ollama_base_url must use HTTPS."
  }
}

variable "api_secret_ids" {
  description = "Secret Manager secret IDs exposed to the API by environment-variable name. Values are secret IDs, never secret values."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for name, secret_id in var.api_secret_ids :
      contains([
        "HUBSPOT_ACCESS_TOKEN",
        "MAILER_INTERNAL_TOKEN",
        "NEWSAPI_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_NUMBER",
      ], name) && can(regex("^[A-Za-z0-9_-]+$", secret_id))
    ])
    error_message = "api_secret_ids contains an unsupported environment name or invalid Secret Manager secret ID."
  }
}
