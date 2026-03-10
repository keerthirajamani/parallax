# Copy this file to terraform.tfvars and fill in your values
# terraform.tfvars is gitignored — never commit secrets here

aws_region   = "us-east-1"
project_name = "my-lambda-app"
environment  = "dev"

# ECR
ecr_repository_name = "parallax/core"
image_tag           = "latest"  # Overridden by CI/CD with git SHA

# VPC
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-east-1a", "us-east-1b"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

# Lambda
lambda_function_name = "parallax-signal-generation"
lambda_memory_size   = 512
lambda_timeout       = 30

lambda_environment_vars = {
  APP_ENV = "dev"
  # Add your env vars here — avoid secrets, use SSM/Secrets Manager instead
}
