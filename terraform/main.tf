terraform {
  backend "s3" {}

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

module "lambda" {
  source = "./modules/lambda"

  ecr_repo_name        = var.ecr_repo_name
  lambda_function_name = var.lambda_function_name
  image_tag            = var.image_tag
  memory_size          = var.memory_size
}