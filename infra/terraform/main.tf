locals {
  services = toset([
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.services
  project  = var.project_id
  service  = each.value

  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "pressradar" {
  location      = var.region
  repository_id = "pressradar"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_firestore_database" "operational" {
  project                           = var.project_id
  name                              = "(default)"
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  deletion_policy                   = "ABANDON"
  delete_protection_state           = "DELETE_PROTECTION_ENABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"

  depends_on = [google_project_service.required]
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "pressradar_analytics"
  location                   = var.region
  delete_contents_on_destroy = false

  depends_on = [google_project_service.required]
}

resource "google_bigquery_table" "product_events" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "product_events"
  deletion_protection = true
  clustering          = ["workspace_id", "name"]
  time_partitioning {
    type  = "DAY"
    field = "occurred_at"
  }
  schema = jsonencode([
    { name = "id", type = "STRING", mode = "REQUIRED" },
    { name = "workspace_id", type = "STRING", mode = "REQUIRED" },
    { name = "name", type = "STRING", mode = "REQUIRED" },
    { name = "occurred_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "opportunity_id", type = "STRING", mode = "REQUIRED" },
    { name = "client_id", type = "STRING", mode = "REQUIRED" },
    { name = "client_name", type = "STRING", mode = "REQUIRED" },
    { name = "source", type = "STRING", mode = "REQUIRED" },
    { name = "relevance_score", type = "INTEGER", mode = "NULLABLE" },
    { name = "detected_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_service_account" "api" {
  account_id   = "pressradar-api"
  display_name = "PressRadar API"
}

resource "google_service_account" "web" {
  account_id   = "pressradar-web"
  display_name = "PressRadar web"
}

data "google_secret_manager_secret" "api" {
  for_each  = var.api_secret_ids
  project   = var.project_id
  secret_id = each.value
}

resource "google_secret_manager_secret_iam_member" "api" {
  for_each  = data.google_secret_manager_secret.api
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_bigquery_dataset_iam_member" "api_analytics" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_bigquery_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "pressradar-api"
  location = var.region

  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }
    containers {
      image = var.api_image
      ports {
        container_port = 8000
      }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
      env {
        name  = "APP_MODE"
        value = "gcp"
      }
      env {
        name  = "API_PORT"
        value = "8000"
      }
      env {
        name  = "WEB_ORIGIN"
        value = var.web_origin
      }
      env {
        name  = "OPERATIONAL_PROVIDER"
        value = "firestore"
      }
      env {
        name  = "ANALYTICS_PROVIDER"
        value = "bigquery"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "FIRESTORE_DATABASE"
        value = google_firestore_database.operational.name
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.analytics.dataset_id
      }
      env {
        name  = "BIGQUERY_EVENTS_TABLE"
        value = google_bigquery_table.product_events.table_id
      }
      env {
        name  = "AI_PROVIDER"
        value = "ollama"
      }
      env {
        name  = "OLLAMA_BASE_URL"
        value = var.ollama_base_url
      }
      dynamic "env" {
        for_each = data.google_secret_manager_secret.api
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.api,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "web" {
  name     = "pressradar-web"
  location = var.region

  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.web.email
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }
    containers {
      image = var.web_image
      ports {
        container_port = 3000
      }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
      env {
        name  = "API_INTERNAL_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "web_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.web.location
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
