resource "aws_security_group" "ec2_sg" {

  vpc_id = var.vpc_id

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

}
