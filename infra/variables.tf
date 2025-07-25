variable "project_name" {
  description = "Prefix for all Azure resources (lowercase letters/numbers, short)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "acr_image_app" {
  description = "ACR image (including tag) for the chat backend, e.g. myacr.azurecr.io/chat-app:latest"
  type        = string
}

variable "acr_image_ollama" {
  description = "ACR image (including tag) for the Ollama server, e.g. myacr.azurecr.io/ollama:latest"
  type        = string
}

variable "storage_account_name" {
  description = "Globally unique name for the Storage Account (3-24 lowercase letters and numbers)"
  type        = string
}

variable "storage_account_share_name" {
  description = "Azure Files share for Ollama model cache"
  type        = string
  default     = "ollama-models"
}