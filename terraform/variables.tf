variable "aws_region" {
  default = "us-east-1"
}

variable "ecr_repo_name" {
  type        = string
  description = "Your existing ECR repo name"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "image_tag" {
  default = "latest"
}

variable "lambda_timeout" {
  default = 30
}

variable "memory_size" {
  default = 512
}

variable "environment" {
  default = "dev"
}