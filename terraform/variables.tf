variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "dev"
}

# ─────────────────────────────
# Lambda Variables (Webhook)
# ─────────────────────────────
variable "lambda_function_name" {
  type        = string
  description = "Name of the webhook Lambda function"
}

variable "lambda_timeout" {
  default     = 30
  description = "Timeout in seconds for the webhook Lambda"
}

variable "memory_size" {
  default     = 512
  description = "Memory size for the webhook Lambda"
}

# ─────────────────────────────
# EC2 Variables (Signal Engine)
# ─────────────────────────────
variable "ecr_repo_name" {
  type        = string
  description = "Your existing ECR repo name"
}

variable "image_tag" {
  default     = "latest"
  description = "Docker image tag to pull onto EC2"
}

variable "ec2_instance_type" {
  default     = "t3.micro"
  description = "Instance type for the Signal Generation Engine"
}