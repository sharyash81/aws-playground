output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.main.bucket
}

output "lambda_python_function_name" {
  description = "Python Lambda function name"
  value       = aws_lambda_function.python_handler.function_name
}

output "lambda_nodejs_function_name" {
  description = "Node.js Lambda function name"
  value       = aws_lambda_function.nodejs_handler.function_name
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/${var.project_name}"
}

output "ec2_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_instance.main.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

output "ec2_key_path" {
  description = "Path to the generated EC2 private key"
  value       = local_sensitive_file.ec2_private_key.filename
}
