variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "aws-playground"
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}


variable "your_ip_cidr" {
  description = "Your public IP in CIDR notation for SSH access, e.g. 1.2.3.4/32"
  type        = string
  default     = "0.0.0.0/0"
}
