variable "aws_region" {}
variable "environment" {}

variable "vpc_cidr" {}
variable "public_subnet_cidr" {}
variable "availability_zone" {}

variable "ecr_repo_name" {}
variable "image_tag" {}

variable "ec2_instance_type" {}

variable "webhook_lambda_function_name" {}
variable "webhook_lambda_memory_size" {}
variable "webhook_lambda_timeout" {}
variable "key_name"{default = "parallax-key-dev" }