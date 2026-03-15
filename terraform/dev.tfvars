aws_region  = "us-east-1"
environment = "dev"

# ECR
ecr_repo_name = "parallax/core"
image_tag     = "latest" # Overridden by CI/CD with git SHA

# EC2
ec2_instance_type = "t3.nano"

# Webhook Lambda
webhook_lambda_function_name = "parallax-signal-generation-webhook-dev"
webhook_lambda_memory_size   = 512
webhook_lambda_timeout       = 300

# VPC
vpc_cidr            = "10.0.0.0/16"
public_subnet_cidr  = "10.0.1.0/24"
availability_zone   = "us-east-1a"