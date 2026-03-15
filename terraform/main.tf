terraform {

  required_version = ">= 1.5.0"

  required_providers {

    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    tls = {
    source = "hashicorp/tls"
    version = "~> 4.0"
  }
  

  }
  
  

  backend "s3" {}

}

provider "aws" {
  region = var.aws_region
}
resource "tls_private_key" "ec2_key" {

  algorithm = "RSA"
  rsa_bits  = 4096

}
resource "aws_key_pair" "parallax_key" {

  key_name   = "parallax-${var.environment}-key"

  public_key = tls_private_key.ec2_key.public_key_openssh

}

resource "local_file" "private_key" {

  filename = "parallax-${var.environment}.pem"

  content  = tls_private_key.ec2_key.private_key_pem

  file_permission = "0400"

}

###################################
# SHARED IAM ROLE
###################################

resource "aws_iam_role" "parallax_role" {

  name = "parallax-${var.environment}-role"

  assume_role_policy = jsonencode({

    Version = "2012-10-17"

    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = [
          "lambda.amazonaws.com",
          "ec2.amazonaws.com"
        ]
      }
      Action = "sts:AssumeRole"
    }]

  })

}

resource "aws_iam_role_policy_attachment" "lambda_logs" {

  role       = aws_iam_role.parallax_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}

resource "aws_iam_role_policy_attachment" "ssm" {

  role       = aws_iam_role.parallax_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"

}

resource "aws_iam_role_policy_attachment" "ecr" {

  role       = aws_iam_role.parallax_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"

}

resource "aws_iam_instance_profile" "ec2_profile" {

  name = "parallax-${var.environment}-profile"
  role = aws_iam_role.parallax_role.name

}

###################################
# VPC MODULE
###################################

module "vpc" {

  source = "./modules/vpc"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  public_subnet_cidr = var.public_subnet_cidr
  availability_zone  = var.availability_zone

}

###################################
# LAMBDA MODULE
###################################

module "lambda" {
  source               = "./modules/lambda"
  lambda_function_name = var.webhook_lambda_function_name
  lambda_memory_size   = var.webhook_lambda_memory_size
  lambda_timeout       = var.webhook_lambda_timeout
  role_arn             = aws_iam_role.parallax_role.arn
  environment          = var.environment

}

###################################
# EC2 MODULE
###################################

data "aws_ecr_repository" "repo" {

  name = var.ecr_repo_name

}

module "ec2" {
  source             = "./modules/ec2"
  environment        = var.environment
  instance_type      = var.ec2_instance_type
  subnet_id          = module.vpc.public_subnet_id
  vpc_id             = module.vpc.vpc_id
  instance_profile   = aws_iam_instance_profile.ec2_profile.name
  ecr_repository_url = data.aws_ecr_repository.repo.repository_url
  image_tag          = var.image_tag
  key_name = aws_key_pair.parallax_key.key_name
}
