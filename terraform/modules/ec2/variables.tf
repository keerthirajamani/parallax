variable "vpc_id" {
  type        = string
  description = "The ID of the VPC"
}

variable "subnet_id" {
  type        = string
  description = "The ID of the subnet to deploy the EC2 instance into"
}

variable "ec2_instance_type" {
  type        = string
  default     = "t3.nano"
  description = "Instance type for the EC2 Instance"
}

variable "ecr_repo_name" {
  type        = string
  description = "Name of the ECR repository"
}

variable "image_tag" {
  type        = string
  description = "Tag of the Docker image to run"
}

variable "lambda_invoke_arn" {
  type        = string
  description = "ARN of the Lambda function to allow the EC2 instance to invoke"
}
