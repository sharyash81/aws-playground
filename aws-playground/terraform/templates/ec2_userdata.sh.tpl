#!/bin/bash
set -e

apt-get update -y
apt-get install -y python3-pip awscli unzip curl

pip3 install boto3

AWS_REGION="${aws_region}"
S3_BUCKET="${s3_bucket}"
LAMBDA_PYTHON="${lambda_python_name}"
LAMBDA_NODEJS="${lambda_nodejs_name}"

echo "=== EC2 Bootstrap: uploading test file to S3 ==="
echo "Hello from EC2 instance at $(date)" > /tmp/ec2_hello.txt
aws s3 cp /tmp/ec2_hello.txt s3://$S3_BUCKET/ec2/ec2_hello.txt --region $AWS_REGION
echo "Upload complete."

echo "=== EC2 Bootstrap: invoking Python Lambda ==="
aws lambda invoke \
  --function-name $LAMBDA_PYTHON \
  --region $AWS_REGION \
  --payload '{"source":"ec2","action":"hello"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda_python_response.json
echo "Python Lambda response:"
cat /tmp/lambda_python_response.json

echo "=== EC2 Bootstrap: invoking Node.js Lambda ==="
aws lambda invoke \
  --function-name $LAMBDA_NODEJS \
  --region $AWS_REGION \
  --payload '{"source":"ec2","action":"hello"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda_nodejs_response.json
echo "Node.js Lambda response:"
cat /tmp/lambda_nodejs_response.json

echo "=== EC2 Bootstrap complete ==="
