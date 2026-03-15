variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "role_arn" {
  type        = string
  description = "IAM Role ARN for the Lambda function"
}

variable "memory_size" {
  type        = number
  default     = 512
}

variable "timeout" {
  type        = number
  default     = 30
}

variable "source_dir" {
  type        = string
  description = "Directory containing the lambda source code"
}