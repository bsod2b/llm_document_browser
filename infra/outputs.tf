output "container_app_fqdn" {
  description = "Public FQDN of the Container App (use this as BACKEND_URL)"
  value       = azurerm_container_app.app.latest_revision_fqdn
}

output "acr_login_server" {
  description = "ACR login server (use this to tag/push your images)"
  value       = azurerm_container_registry.acr.login_server
}

output "storage_account_name" {
  value = azurerm_storage_account.sa.name
}

output "storage_share_name" {
  value = azurerm_storage_share.models.name
}
