.PHONY: help init deploy destroy outputs \
        test-s3-upload test-s3-download test-s3-multipart \
        test-lambda-python test-lambda-nodejs test-lambda-api \
        test-lambda-manager \
        ec2-start ec2-stop ec2-ssh

SHELL := /bin/bash
TF_DIR := terraform
SCRIPTS := scripts
REGION  := us-east-1

# ── Helpers ──────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AWS Playground — Makefile targets"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make init          Terraform init"
	@echo "    make deploy        Terraform apply (creates all AWS resources)"
	@echo "    make destroy       Terraform destroy (removes all AWS resources)"
	@echo "    make outputs       Show Terraform outputs"
	@echo ""
	@echo "  S3 tests:"
	@echo "    make test-s3-upload      Upload a test file to S3"
	@echo "    make test-s3-download    Download the test file from S3"
	@echo "    make test-s3-multipart   Multipart upload/download (generates 20 MB file)"
	@echo ""
	@echo "  Lambda tests:"
	@echo "    make test-lambda-python  Invoke Python Lambda via SDK"
	@echo "    make test-lambda-nodejs  Invoke Node.js Lambda via SDK"
	@echo "    make test-lambda-api     Invoke Python Lambda via API Gateway"
	@echo ""
	@echo "  Lambda Manager:"
	@echo "    make test-lambda-manager Run fan-out of 100 invocations"
	@echo ""
	@echo "  EC2:"
	@echo "    make ec2-start     Start the EC2 instance"
	@echo "    make ec2-stop      Stop the EC2 instance"
	@echo "    make ec2-ssh       SSH into the EC2 instance"
	@echo ""

# ── Terraform ─────────────────────────────────────────────────────────────────
init:
	terraform -chdir=$(TF_DIR) init

deploy:
	terraform -chdir=$(TF_DIR) apply -auto-approve

destroy:
	terraform -chdir=$(TF_DIR) destroy -auto-approve

outputs:
	terraform -chdir=$(TF_DIR) output

# ── Shared: read TF outputs ───────────────────────────────────────────────────
BUCKET        := $(shell terraform -chdir=$(TF_DIR) output -raw s3_bucket_name 2>/dev/null)
LAMBDA_PYTHON := $(shell terraform -chdir=$(TF_DIR) output -raw lambda_python_function_name 2>/dev/null)
LAMBDA_NODEJS := $(shell terraform -chdir=$(TF_DIR) output -raw lambda_nodejs_function_name 2>/dev/null)
API_URL       := $(shell terraform -chdir=$(TF_DIR) output -raw api_gateway_url 2>/dev/null)
EC2_ID        := $(shell terraform -chdir=$(TF_DIR) output -raw ec2_instance_id 2>/dev/null)
EC2_IP        := $(shell terraform -chdir=$(TF_DIR) output -raw ec2_public_ip 2>/dev/null)

# ── S3 tests ──────────────────────────────────────────────────────────────────
test-s3-upload:
	@echo "Hello from aws-playground at $$(date)" > /tmp/test_upload.txt
	python3 $(SCRIPTS)/s3_upload.py /tmp/test_upload.txt $(BUCKET) --key test/hello.txt

test-s3-download:
	python3 $(SCRIPTS)/s3_download.py $(BUCKET) test/hello.txt --output /tmp/test_download.txt
	@echo "--- Downloaded content ---"
	@cat /tmp/test_download.txt

test-s3-multipart:
	python3 $(SCRIPTS)/s3_multipart.py generate /tmp/test_large.bin --size-mb 20
	python3 $(SCRIPTS)/s3_multipart.py upload /tmp/test_large.bin $(BUCKET) --key test/large.bin
	python3 $(SCRIPTS)/s3_multipart.py download $(BUCKET) test/large.bin --output /tmp/test_large_dl.bin
	@echo "--- Verifying file integrity ---"
	@md5sum /tmp/test_large.bin /tmp/test_large_dl.bin

# ── Lambda tests ──────────────────────────────────────────────────────────────
test-lambda-python:
	python3 $(SCRIPTS)/lambda_invoke.py $(LAMBDA_PYTHON) \
		--payload '{"action":"hello","source":"makefile"}' \
		--region $(REGION)
	@echo ""
	python3 $(SCRIPTS)/lambda_invoke.py $(LAMBDA_PYTHON) \
		--payload '{"action":"s3_write","key":"lambda-test/python.txt","content":"Hello from Python Lambda!"}' \
		--region $(REGION)

test-lambda-nodejs:
	python3 $(SCRIPTS)/lambda_invoke.py $(LAMBDA_NODEJS) \
		--payload '{"action":"hello","source":"makefile"}' \
		--region $(REGION)
	@echo ""
	python3 $(SCRIPTS)/lambda_invoke.py $(LAMBDA_NODEJS) \
		--payload '{"action":"s3_write","key":"lambda-test/nodejs.txt","content":"Hello from Node.js Lambda!"}' \
		--region $(REGION)

test-lambda-api:
	bash $(SCRIPTS)/lambda_invoke_api.sh $(API_URL) '{"action":"hello","source":"api_gateway"}'

# ── Lambda Manager ────────────────────────────────────────────────────────────
test-lambda-manager:
	python3 $(SCRIPTS)/lambda_manager.py \
		--region $(REGION) \
		--concurrency 5 \
		--output /tmp/lambda_manager_results.json \
		fan-out \
		--function $(LAMBDA_PYTHON) \
		--count 10 \
		--payload '{"action":"hello","source":"lambda_manager"}'
	@echo ""
	@echo "Results saved to /tmp/lambda_manager_results.json"

# ── EC2 ───────────────────────────────────────────────────────────────────────
ec2-start:
	aws ec2 start-instances --instance-ids $(EC2_ID) --region $(REGION)
	aws ec2 wait instance-running --instance-ids $(EC2_ID) --region $(REGION)
	@echo "EC2 instance $(EC2_ID) is running"

ec2-stop:
	aws ec2 stop-instances --instance-ids $(EC2_ID) --region $(REGION)
	@echo "EC2 instance $(EC2_ID) stop initiated"

ec2-ssh:
	ssh -i $${EC2_KEY:-ec2_key.pem} -o StrictHostKeyChecking=no ubuntu@$(EC2_IP)
