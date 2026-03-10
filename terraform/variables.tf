variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "my-lambda-app"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ── ECR ───────────────────────────────────────
variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "my-lambda-app"
}

variable "image_tag" {
  description = "Docker image tag to deploy (passed by CI/CD)"
  type        = string
  default     = "latest"
}

# ── VPC ───────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (Lambda runs here)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (NAT Gateway lives here)"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# ── Lambda ────────────────────────────────────
variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "my-lambda-function"
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_environment_vars" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}
