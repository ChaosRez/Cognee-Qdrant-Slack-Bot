variable "project_id" {
  description = "Google Cloud project that will serve Vertex AI requests."
  type        = string
}

variable "principal" {
  description = "Optional IAM principal granted Vertex AI User, for example user:name@example.com."
  type        = string
  default     = ""
}

variable "location" {
  description = "Vertex AI location exported for LiteLLM."
  type        = string
  default     = "global"
}

variable "model" {
  description = "Lightweight Gemini model used by the Slack bot."
  type        = string
  default     = "gemini-3.1-flash-lite"
}
