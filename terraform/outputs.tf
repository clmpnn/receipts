output "managed_schema_name" {
  description = "The name of the schema managed by Terraform"
  value       = postgresql_schema.app_schema.name
}