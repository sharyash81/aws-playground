# AWS Playground

Automated AWS internship introduction tasks covering S3, Lambda, and EC2.

## Project Structure

```
aws-playground/
├── terraform/
│   ├── main.tf          # Provider + random suffix
│   ├── variables.tf     # Input variables
│   ├── outputs.tf       # Output values (bucket name, URLs, IPs)
│   ├── s3.tf            # S3 bucket (versioning, encryption, private)
│   ├── iam.tf           # IAM roles for Lambda + EC2
│   ├── lambda.tf        # Python & Node.js Lambda + API Gateway (HTTP)
│   ├── ec2.tf           # EC2 Ubuntu 22.04 instance
│   └── templates/
│       └── ec2_userdata.sh.tpl  # Bootstrap: uploads to S3, invokes Lambda
├── lambda/
│   ├── python/handler.py        # Python 3.12 Lambda (hello, s3_write, s3_read)
│   └── nodejs/handler.js        # Node.js 20.x Lambda (hello, s3_write, s3_read)
├── scripts/
│   ├── s3_upload.py             # Single-part S3 upload
│   ├── s3_download.py           # Single-part S3 download
│   ├── s3_multipart.py          # Multipart upload/download with progress bar
│   ├── lambda_invoke.py         # Invoke a Lambda via SDK
│   ├── lambda_invoke_api.sh     # Invoke Lambda via API Gateway (curl)
│   └── lambda_manager.py        # Fan-out manager: invoke 100s of Lambdas concurrently
├── Makefile                     # One-command runner for all tasks
└── README.md
```

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured (`aws configure`)
- Python 3.12+ with `boto3` (`pip install boto3`)
- An existing EC2 key pair in AWS (optional, for SSH access)

## Quick Start

### 1. Configure variables

Edit `terraform/variables.tf` or create a `terraform/terraform.tfvars`:

```hcl
aws_region        = "us-east-1"
project_name      = "aws-playground"
ec2_key_pair_name = "my-key-pair"   # optional, for SSH
your_ip_cidr      = "1.2.3.4/32"   # your IP for SSH security group
```

### 2. Deploy everything

```bash
make init
make deploy
make outputs
```

### 3. Run S3 tests

```bash
make test-s3-upload       # Upload a small test file
make test-s3-download     # Download it back
make test-s3-multipart    # Generate 20 MB file, multipart upload + download + verify
```

### 4. Run Lambda tests

```bash
make test-lambda-python   # Invoke Python Lambda (hello + s3_write)
make test-lambda-nodejs   # Invoke Node.js Lambda (hello + s3_write)
make test-lambda-api      # Invoke Python Lambda via API Gateway URL
```

### 5. Run Lambda Manager (fan-out 100 invocations)

```bash
make test-lambda-manager
```

Output:
```
[INFO] Dispatching 100 invocations | concurrency=50 | region=us-east-1

  [████████████████████████████████████████] 100/100 (100%)  ✓100 ✗0  42.3 inv/s  2.4s

============================================================
  Total:     100
  Succeeded: 100
  Failed:    0
  Elapsed:   2.36s
  Avg rate:  42.4 inv/s
============================================================
```

### 6. EC2 operations

```bash
make ec2-start                        # Start the instance
make ec2-stop                         # Stop the instance
make ec2-ssh EC2_KEY=~/.ssh/key.pem   # SSH in
```

The EC2 instance automatically runs a bootstrap script on first boot that:
- Uploads a file to S3
- Invokes both the Python and Node.js Lambda functions

### 7. Destroy everything

```bash
make destroy
```

---

## Lambda Manager — Advanced Usage

The `scripts/lambda_manager.py` supports three modes:

### Fan-out: same function, N times

```bash
python3 scripts/lambda_manager.py fan-out \
    --function my-function \
    --count 10 \
    --payload '{"action":"hello"}' \
    --concurrency 5 \
    --output results.json
```

### Distribute: list of distinct task payloads

Create `tasks.json`:
```json
[
  {"action": "s3_write", "key": "task/0.txt", "content": "task 0"},
  {"action": "s3_write", "key": "task/1.txt", "content": "task 1"}
]
```

```bash
python3 scripts/lambda_manager.py distribute \
    --function my-function \
    --tasks tasks.json \
    --concurrency 50
```

### Multi-function: invoke different functions each once

```bash
python3 scripts/lambda_manager.py multi \
    --functions fn-a fn-b fn-c \
    --payload '{"action":"hello"}'
```

---

## Lambda Actions

Both Python and Node.js Lambdas support the same `action` field:

| Action | Description |
|--------|-------------|
| `hello` | Returns a greeting with runtime info and timestamp |
| `s3_write` | Writes `content` to S3 at `key` |
| `s3_read` | Reads and returns content from S3 at `key` |

Example payload:
```json
{"action": "s3_write", "key": "output/result.txt", "content": "Hello World"}
```
