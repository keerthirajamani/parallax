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

# Get existing ECR repo
data "aws_ecr_repository" "lambda_repo" {
  name = var.ecr_repo_name
}

# ─────────────────────────────
# IAM Role for Lambda
# ─────────────────────────────
data "aws_iam_role" "lambda_exec_role" {
  name = "parallax-signal-generation-role"
}

# ─────────────────────────────
# Lambda Function
# ─────────────────────────────
resource "aws_lambda_function" "lambda" {
  function_name = var.lambda_function_name
  role          = data.aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"

  image_uri = "${data.aws_ecr_repository.lambda_repo.repository_url}:${var.image_tag}"

  memory_size = var.memory_size
  timeout     = var.lambda_timeout
}
