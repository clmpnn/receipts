variable "db_host" {
  description = "Neon Postgres host endpoint"
  type        = string
}

variable "db_port" {
  description = "Postgres port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "neondb"
}

variable "db_user" {
  description = "Postgres user"
  type        = string
}

variable "db_password" {
  description = "Postgres password"
  type        = string
  sensitive   = true
}