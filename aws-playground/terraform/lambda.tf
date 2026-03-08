### Package Lambda source code ###
data "archive_file" "python_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/python"
  output_path = "${path.module}/../lambda/python_handler.zip"
}

data "archive_file" "nodejs_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/nodejs"
  output_path = "${path.module}/../lambda/nodejs_handler.zip"
}

### Python Lambda ###
resource "aws_lambda_function" "python_handler" {
  function_name    = "${var.project_name}-python-${random_id.suffix.hex}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.python_lambda.output_path
  source_code_hash = data.archive_file.python_lambda.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.main.bucket
    }
  }

  tags = { Project = var.project_name }
}

### Node.js Lambda ###
resource "aws_lambda_function" "nodejs_handler" {
  function_name    = "${var.project_name}-nodejs-${random_id.suffix.hex}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambdaHandler"
  runtime          = "nodejs20.x"
  filename         = data.archive_file.nodejs_lambda.output_path
  source_code_hash = data.archive_file.nodejs_lambda.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.main.bucket
    }
  }

  tags = { Project = var.project_name }
}

### API Gateway (HTTP API) ###
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project_name}-api-${random_id.suffix.hex}"
  protocol_type = "HTTP"

  tags = { Project = var.project_name }
}

resource "aws_apigatewayv2_integration" "python_lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.python_handler.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "python_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /${var.project_name}"
  target    = "integrations/${aws_apigatewayv2_integration.python_lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gw_python" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.python_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
