terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "us-east-1-parallax-bucket"
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
  instance_type          = "t3.small"
  key_name               = var.key_pair_name
  subnet_id              = aws_subnet.parallax.id
  vpc_security_group_ids = [aws_security_group.parallax.id]
  iam_instance_profile   = aws_iam_instance_profile.parallax.name

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y docker cronie awscli

    curl -1sLf 'https://dl.redpanda.com/nZEXoJh8/redpanda/setup.rpm.sh' | bash
    dnf install -y redpanda
    rpk redpanda config set redpanda.developer_mode true
    rpk redpanda config set redpanda.cloud_storage_enabled true
    rpk redpanda config set redpanda.cloud_storage_region us-east-1
    rpk redpanda config set redpanda.cloud_storage_bucket us-east-1-parallax-redpanda
    rpk redpanda config set redpanda.cloud_storage_credentials_source aws_instance_metadata
    systemctl enable redpanda
    systemctl start redpanda

    systemctl enable docker crond
    systemctl start docker crond
    usermod -aG docker ec2-user

    sleep 15
    rpk topic create parallax-signals-india \
      -c redpanda.remote.write=true \
      -c redpanda.remote.read=true
    rpk topic create parallax-signals-us \
      -c redpanda.remote.write=true \
      -c redpanda.remote.read=true
  EOF

  tags = {
    Name = "parallax"
  }
}

# ── Redpanda Tiered Storage Bucket ───────────────────────────────────────────

resource "aws_s3_bucket" "redpanda" {
  bucket = "us-east-1-parallax-redpanda"
  tags   = { Name = "parallax-redpanda" }
}

resource "aws_s3_bucket_lifecycle_configuration" "redpanda" {
  bucket = aws_s3_bucket.redpanda.id

  rule {
    id     = "expire-old-segments"
    status = "Enabled"

    filter {}

    expiration {
      days = 180
    }
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
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = "arn:aws:s3:::${var.s3_bucket}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload"
        ]
        Resource = "arn:aws:s3:::us-east-1-parallax-redpanda/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = "arn:aws:s3:::us-east-1-parallax-redpanda"
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
