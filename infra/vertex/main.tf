provider "google" {
  project = var.project_id
}

resource "google_project_service" "vertex_ai" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_iam_member" "vertex_user" {
  count = var.principal == "" ? 0 : 1

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = var.principal

  depends_on = [google_project_service.vertex_ai]
}

output "env" {
  description = "Non-secret environment values for the Slack bot."
  value = {
    LLM_BACKEND       = "vertex"
    VERTEXAI_PROJECT  = var.project_id
    VERTEXAI_LOCATION = var.location
    VERTEX_MODEL      = var.model
  }
}
