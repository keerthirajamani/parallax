aws_region  = "us-east-1"
environment = "dev"

# ECR
ecr_repo_name = "parallax/core"
image_tag     = "latest" # Overridden by CI/CD with git SHA

# Lambda
lambda_function_name = "parallax-signal-generation"
lambda_memory_size   = 512
lambda_timeout       = 30
