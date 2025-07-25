############################################
# Random suffix to avoid global name clashes
############################################
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  numeric = true
  special = false
}

############################################
# Resource Group
############################################
resource "azurerm_resource_group" "rg" {
  name     = "${var.project_name}-rg"
  location = var.location
  tags     = var.tags
}

############################################
# Log Analytics (needed by Container Apps Env)
############################################
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.project_name}-law-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

############################################
# Container Apps Environment
############################################
resource "azurerm_container_app_environment" "cae" {
  name                       = "${var.project_name}-cae-${random_string.suffix.result}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  tags                       = var.tags
}

############################################
# Azure Container Registry (simple: admin enabled)
############################################
resource "azurerm_container_registry" "acr" {
  name                = "${var.project_name}acr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.tags
}

############################################
# Storage Account + Azure Files for Ollama models
############################################
resource "azurerm_storage_account" "sa" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.tags
}

resource "azurerm_storage_share" "models" {
  name                 = var.storage_account_share_name
  storage_account_name = azurerm_storage_account.sa.name
  quota                = 64
}

# Wire the Azure Files share into the Container App Environment
resource "azurerm_container_app_environment_storage" "ollama_storage" {
  name                         = "ollama-models"
  container_app_environment_id = azurerm_container_app_environment.cae.id

  account_name = azurerm_storage_account.sa.name
  access_key  = azurerm_storage_account.sa.primary_access_key
  share_name   = azurerm_storage_share.models.name
  access_mode  = "ReadWrite"
}

############################################
# Container App (multi-container, http_scale_rule)
############################################
resource "azurerm_container_app" "app" {
  name                         = "${var.project_name}-chat"
  resource_group_name          = azurerm_resource_group.rg.name
  container_app_environment_id = azurerm_container_app_environment.cae.id
  revision_mode                = "Single"
  tags                         = var.tags

  # In the current provider, a traffic_weight block is still required.
  # (Even though the docs imply it's for Multiple mode.) 
  # Ref: provider issue. 
  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  ########################
  # Registry auth via Secret
  ########################
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  ########################################
  # Template: 2 containers + scale + volume
  ########################################
  template {
    min_replicas = 0
    max_replicas = 3

    # ---- HTTP scale rule (KEDA under the hood) ----
    http_scale_rule {
      name                 = "http"
      concurrent_requests  = 100
    }

    # ---- Container A: your backend ----
    container {
      name   = "chat-backend"
      image  = var.acr_image_app
      cpu    = 1.0
      memory = "2.0Gi"

      env {
        name  = "OLLAMA_URL"
        value = "http://localhost:11434"
      }

      # Probes are optional, add if you have /healthz, etc.
      # liveness_probe {
      #   transport               = "HTTP"
      #   port                    = 8080
      #   path                    = "/healthz"
      #   initial_delay           = 5
      #   interval_seconds        = 10
      #   failure_count_threshold = 3
      #   timeout                 = 2
      # }
    }

    # ---- Container B: Ollama sidecar ----
    container {
      name   = "ollama"
      image  = var.acr_image_ollama
      cpu    = 2.0
      memory = "8.0Gi"

      env {
        name  = "OLLAMA_HOST"
        value = "0.0.0.0:11434"
      }

      volume_mounts {
        name = "ollama-models"
        path = "/root/.ollama"
      }
    }

    # ---- Volume referencing the Environment Storage ----
    volume {
      name          = "ollama-models"
      storage_type  = "AzureFile"
      storage_name  = azurerm_container_app_environment_storage.ollama_storage.name
      # mount_options = "dir_mode=0755,file_mode=0644" # optional
    }
  }
}
