terraform {
  required_version = ">= 1.5.0"

  required_providers {
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.22.0"
    }
  }
}

provider "postgresql" {
  host            = var.db_host
  port            = var.db_port
  database        = var.db_name
  username        = var.db_user
  password        = var.db_password
  sslmode         = "require"
  connect_timeout = 15
}

resource "postgresql_schema" "app_schema" {
  name  = "receipts_app"
  owner = var.db_user
}