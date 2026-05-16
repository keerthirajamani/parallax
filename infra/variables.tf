variable "aws_region" {
  default = "us-east-1"
}

variable "key_pair_name" {
  description = "Name of your existing EC2 key pair"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed for SSH access"
  default     = "0.0.0.0/0"
}

variable "s3_bucket" {
  default = "us-east-1-parallax-bucket"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance. Pin explicitly to avoid unplanned instance replacement."
  type        = string
}