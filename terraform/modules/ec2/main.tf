# 1. Security Group for EC2 (Outbound only for APIs)
resource "aws_security_group" "ec2_sg" {
  name        = "parallax-ec2-sg"
  description = "Security group for Parallax Signal Generation EC2 Instance"
  vpc_id      = var.vpc_id

  # No Inbound rules! We will use SSM Session Manager to connect to it securely.

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "parallax-ec2-sg"
  }
}

# 2. IAM Role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "parallax-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Effect = "Allow"
    }]
  })
}

# Attach core permissions for SSM (No-SSH terminal access)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach permissions to pull from ECR
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Attach custom policy to allow triggering the Lambda function
resource "aws_iam_role_policy" "lambda_invoke_policy" {
  name = "allow-lambda-invoke"
  role = aws_iam_role.ec2_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "lambda:InvokeFunction"
      ]
      Effect   = "Allow"
      Resource = var.lambda_invoke_arn
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "parallax-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# 3. Find latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# 4. Create EC2 Instance
resource "aws_instance" "signal_engine" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = var.ec2_instance_type
  
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  subnet_id              = var.subnet_id

  # This script runs exactly once when the EC2 instance boots up for the very first time.
  # It installs docker, logs into ECR, pulls the image, and runs it!
  user_data = <<-EOF
    #!/bin/bash
    set -x

    # Install dependencies
    dnf update -y
    dnf install -y docker
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user

    # Fetch AWS Account ID dynamically
    TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
    REGION=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" -s http://169.254.169.254/latest/meta-data/placement/region)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)

    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

    # Construct the Full ECR Image URI
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/${var.ecr_repo_name}:${var.image_tag}"

    # Pull the Docker image
    docker pull $IMAGE_URI

    # Run the Docker image in detached mode (--restart unless-stopped keeps it alive)
    docker run -d --name parallax_signal_engine --restart unless-stopped $IMAGE_URI
    EOF

  # Replace the instance if the user_data (image tag) changes
  user_data_replace_on_change = true

  tags = {
    Name = "parallax-signal-generation-engine"
  }
}
