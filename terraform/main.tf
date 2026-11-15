terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "Region de AWS para el despliegue"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Prefijo para los recursos del microservicio"
  type        = string
  default     = "blacklist"
}

variable "codebuild_role_name" {
  description = "Nombre del rol IAM existente de AWS CodeBuild (Entrega 2)"
  type        = string
  default     = "codebuild-blacklist-build-service-role"
}

# VPC y subredes públicas por defecto de la cuenta de AWS
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
