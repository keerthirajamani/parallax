# ──────────────────────────────────────────────
# VPC
# ──────────────────────────────────────────────
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, { Name = "${var.project_name}-vpc" })
}

# ──────────────────────────────────────────────
# Internet Gateway (for public subnets)
# ──────────────────────────────────────────────
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "${var.project_name}-igw" })
}

# ──────────────────────────────────────────────
# Public Subnets (one per AZ — hosts NAT GW)
# ──────────────────────────────────────────────
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  })
}

# ──────────────────────────────────────────────
# Private Subnets (one per AZ — Lambda runs here)
# ──────────────────────────────────────────────
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.project_name}-private-${var.availability_zones[count.index]}"
    Tier = "private"
  })
}

# ──────────────────────────────────────────────
# Elastic IPs for NAT Gateways
# ──────────────────────────────────────────────
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.project_name}-eip-${var.availability_zones[count.index]}"
  })

  depends_on = [aws_internet_gateway.this]
}

# ──────────────────────────────────────────────
# NAT Gateways — one per AZ for true HA
# Each private subnet routes through its AZ's NAT GW
# ──────────────────────────────────────────────
resource "aws_nat_gateway" "this" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${var.project_name}-nat-${var.availability_zones[count.index]}"
  })

  depends_on = [aws_internet_gateway.this]
}

# ──────────────────────────────────────────────
# Route Tables
# ──────────────────────────────────────────────

# Public route table — routes internet traffic via IGW
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, { Name = "${var.project_name}-rt-public" })
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route tables — one per AZ, routes internet via that AZ's NAT GW
resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index].id
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-rt-private-${var.availability_zones[count.index]}"
  })
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ──────────────────────────────────────────────
# Security Group for Lambda
# ──────────────────────────────────────────────
resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg"
  description = "Security group for Lambda — outbound only"
  vpc_id      = aws_vpc.this.id

  # No inbound rules — Lambda is invoked via AWS APIs, not direct network calls

  egress {
    description = "HTTPS to internet (ECR, S3, AWS APIs)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-lambda-sg" })
}

# ──────────────────────────────────────────────
# VPC Endpoints (optional but recommended)
# Allows Lambda to reach S3/ECR without NAT costs
# ──────────────────────────────────────────────
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = merge(var.tags, { Name = "${var.project_name}-s3-endpoint" })
}

data "aws_region" "current" {}
