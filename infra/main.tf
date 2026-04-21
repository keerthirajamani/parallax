terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "nse-artifacts"
    key     = "parallax-state-artifacts/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Data ──────────────────────────────────────────────────────────────────────

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# ── VPC ───────────────────────────────────────────────────────────────────────

resource "aws_vpc" "parallax" {
  cidr_block = "10.0.0.0/16"
  tags       = { Name = "parallax-vpc" }
}

resource "aws_subnet" "parallax" {
  vpc_id                  = aws_vpc.parallax.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  tags                    = { Name = "parallax-subnet" }
}

resource "aws_internet_gateway" "parallax" {
  vpc_id = aws_vpc.parallax.id
  tags   = { Name = "parallax-igw" }
}

resource "aws_route_table" "parallax" {
  vpc_id = aws_vpc.parallax.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.parallax.id
  }

  tags = { Name = "parallax-rt" }
}

resource "aws_route_table_association" "parallax" {
  subnet_id      = aws_subnet.parallax.id
  route_table_id = aws_route_table.parallax.id
}

# ── Security Group ────────────────────────────────────────────────────────────

resource "aws_security_group" "parallax" {
  name        = "parallax-sg"
  description = "Allow SSH inbound, all outbound"
  vpc_id      = aws_vpc.parallax.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── EC2 Instance ──────────────────────────────────────────────────────────────

resource "aws_instance" "parallax" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.nano"
  key_name               = var.key_pair_name
  subnet_id              = aws_subnet.parallax.id
  vpc_security_group_ids = [aws_security_group.parallax.id]
  iam_instance_profile   = aws_iam_instance_profile.parallax.name

  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y docker cronie awscli
    systemctl enable docker crond
    systemctl start docker crond
    usermod -aG docker ec2-user
  EOF

  tags = {
    Name = "parallax"
  }
}

# ── Elastic IP (free while instance is running) ───────────────────────────────

resource "aws_eip" "parallax" {
  instance = aws_instance.parallax.id
  domain   = "vpc"

  tags = {
    Name = "parallax-eip"
  }
}

# ── IAM Role (S3 + ECR access) ────────────────────────────────────────────────

resource "aws_iam_role" "parallax" {
  name = "parallax-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "parallax" {
  name = "parallax-policy"
  role = aws_iam_role.parallax.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "parallax" {
  name = "parallax-ec2-profile"
  role = aws_iam_role.parallax.name
}
