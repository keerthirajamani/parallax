resource "aws_security_group" "ec2_sg" {

  vpc_id = var.vpc_id
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # Better to restrict to your IP
  }

  egress {

    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]

  }

}

data "aws_ami" "amazon_linux" {

  most_recent = true
  owners      = ["amazon"]

  filter {

    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]

  }

}

resource "aws_instance" "signal_engine" {

  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  subnet_id = var.subnet_id

  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  iam_instance_profile = var.instance_profile

  key_name = var.key_name

  tags = {
    Name        = "parallax-${var.environment}-signal-engine"
    Environment = var.environment
    Project     = "parallax"
  }

  user_data = <<-EOF
  #!/bin/bash

  dnf update -y
  dnf install -y docker awscli cronie

  systemctl enable docker
  systemctl start docker

  # Enable cron
  systemctl enable crond
  systemctl start crond

  # Login to ECR
  aws ecr get-login-password --region ${var.aws_region} \
  | docker login \
  --username AWS \
  --password-stdin ${var.ecr_repository_url}

  # Create run script
  cat <<SCRIPT > /home/ec2-user/run_signal_engine.sh
  #!/bin/bash

  docker pull ${var.ecr_repository_url}:${var.image_tag}

  docker stop signal_engine || true
  docker rm signal_engine || true

  docker run -d \
  --name signal_engine \
  ${var.ecr_repository_url}:${var.image_tag}

  SCRIPT

  chmod +x /home/ec2-user/run_signal_engine.sh
  chown ec2-user:ec2-user /home/ec2-user/run_signal_engine.sh

  # Run immediately once
  /home/ec2-user/run_signal_engine.sh

  # Setup cron for ec2-user
  echo "0 */2 * * * /home/ec2-user/run_signal_engine.sh" > /tmp/cronjob
  sudo crontab -u ec2-user /tmp/cronjob

  EOF

}