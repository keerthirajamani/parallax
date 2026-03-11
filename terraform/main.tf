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

# ──────────────────────────────────────────────
# ECR Repository
# ──────────────────────────────────────────────
# module "ecr" {
#   source          = "./modules/ecr"
#   repository_name = var.ecr_repository_name
#   tags            = local.common_tags
# }

# ──────────────────────────────────────────────
# VPC
# ──────────────────────────────────────────────
data "aws_ecr_repository" "lambda_repo" {
  name = var.ecr_repository_name
}

module "vpc" {
  source               = "./modules/vpc"
  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  private_subnet_cidrs = var.private_subnet_cidrs
  public_subnet_cidrs  = var.public_subnet_cidrs
  tags                 = local.common_tags
}

# ──────────────────────────────────────────────
# Lambda
# ──────────────────────────────────────────────
module "lambda" {
  source = "./modules/lambda"

  function_name      = var.lambda_function_name
  image_uri          = "${data.aws_ecr_repository.lambda_repo.repository_url}:${var.image_tag}"
  memory_size        = var.lambda_memory_size
  timeout            = var.lambda_timeout
  environment_vars   = var.lambda_environment_vars
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.lambda_security_group_id]
  tags               = local.common_tags

  # depends_on = [module.ecr, module.vpc]
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
