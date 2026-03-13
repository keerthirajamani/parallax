variable "ecr_repo_name" {
  type        = string
  description = "Existing ECR repo name"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "ECR image tag"
}

variable "lambda_timeout" {
  type        = number
  default     = 30
  description = "Lambda timeout in seconds"
}

variable "memory_size" {
  type        = number
  default     = 512
  description = "Lambda memory in MB"
}

variable "environment" {
  default = "dev"
}
variable "bucket_name" {
  default="datahub-market-data-live"
}