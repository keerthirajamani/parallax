terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "parallax-terraform-state-bucket"
    key    = "parallax/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# ==============================================================================
# DATA SOURCES & EXISTING INFRASTRUCTURE
# ==============================================================================

# Get existing IAM role for Lambda
data "aws_iam_role" "lambda_exec_role" {
  name = "parallax-signal-generation-role"
}

# ==============================================================================
# MODULES
# ==============================================================================

module "vpc" {
  source = "./modules/vpc"
}

module "lambda" {
  source        = "./modules/lambda"
  
  function_name = var.lambda_function_name
  role_arn      = data.aws_iam_role.lambda_exec_role.arn
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout
  source_dir    = "${path.module}/../lambda_handlers"
}

module "ec2" {
  source = "./modules/ec2"
  
  vpc_id            = module.vpc.vpc_id
  subnet_id         = module.vpc.public_subnet_id
  ec2_instance_type = var.ec2_instance_type
  ecr_repo_name     = var.ecr_repo_name
  image_tag         = var.image_tag
  lambda_invoke_arn = module.lambda.function_arn
}
