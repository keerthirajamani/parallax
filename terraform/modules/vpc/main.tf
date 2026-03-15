resource "aws_vpc" "parallax" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "parallax-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.parallax.id

  tags = {
    Name = "parallax-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.parallax.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  
  tags = {
    Name = "parallax-public-subnet"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.parallax.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "parallax-public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}
