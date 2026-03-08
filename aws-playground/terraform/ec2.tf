resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "ec2_key" {
  key_name   = "${var.project_name}-key-${random_id.suffix.hex}"
  public_key = tls_private_key.ec2_key.public_key_openssh
}

resource "local_sensitive_file" "ec2_private_key" {
  content         = tls_private_key.ec2_key.private_key_pem
  filename        = "${path.root}/../ec2_key.pem"
  file_permission = "0400"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg-${random_id.suffix.hex}"
  description = "Allow SSH inbound, all outbound"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = var.project_name }
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.ec2_instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  key_name               = aws_key_pair.ec2_key.key_name

  user_data = templatefile("${path.module}/templates/ec2_userdata.sh.tpl", {
    s3_bucket            = aws_s3_bucket.main.bucket
    lambda_python_name   = aws_lambda_function.python_handler.function_name
    lambda_nodejs_name   = aws_lambda_function.nodejs_handler.function_name
    aws_region           = var.aws_region
  })

  tags = {
    Name    = "${var.project_name}-ec2"
    Project = var.project_name
  }
}
