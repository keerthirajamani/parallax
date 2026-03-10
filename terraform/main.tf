terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use S3 backend for remote state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "lambda/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-state-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

# ──────────────────────────────────────────────
# ECR Repository
# ──────────────────────────────────────────────
module "ecr" {
  source          = "./modules/ecr"
  repository_name = var.ecr_repository_name
}

# ──────────────────────────────────────────────
# VPC
# ──────────────────────────────────────────────
module "vpc" {
  source              = "./modules/vpc"
  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  private_subnet_cidrs = var.private_subnet_cidrs
  public_subnet_cidrs  = var.public_subnet_cidrs
  tags                = local.common_tags
}

# ──────────────────────────────────────────────
# Lambda
# ──────────────────────────────────────────────
module "lambda" {
  source = "./modules/lambda"

  function_name       = var.lambda_function_name
  image_uri           = "${module.ecr.repository_url}:${var.image_tag}"
  lambda_role_arn     = module.lambda.role_arn
  memory_size         = var.lambda_memory_size
  timeout             = var.lambda_timeout
  environment_vars    = var.lambda_environment_vars

  # VPC config
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.lambda_security_group_id]

  tags = local.common_tags

  depends_on = [module.ecr, module.vpc]
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
