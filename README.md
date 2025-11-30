# Serverless Data-Ingestion Pipeline
## LocalStack vs AWS Learner Lab

A production-ready serverless data ingestion pipeline that runs identically on LocalStack (local) and AWS Learner Lab, deployed with Terraform and instrumented with CloudWatch metrics.

## Architecture

```
CSV Upload → S3 (uploads/) → Lambda Processor → {
  - Infer schema
  - Compute statistics  
  - Detect quality issues
  - Generate summary JSON → S3 (processed/)
  - Write metadata → DynamoDB
}
```

### Components

- **S3 Bucket**: `uploads/` for incoming CSV files, `processed/` for results
- **Lambda Function**: Processes CSV files, computes stats, detects issues
- **DynamoDB Table**: Stores file metadata with `file_name` as partition key
- **CloudWatch**: Metrics for Lambda and DynamoDB performance

## Prerequisites

### For LocalStack
- Docker Desktop
- Python 3.9+
- Terraform 1.0+
- AWS CLI configured

### For AWS Learner Lab
- Active AWS Learner Lab session
- AWS CLI configured with lab credentials
- Terraform 1.0+

## Quick Start

### 1. LocalStack Deployment

```bash
# Start LocalStack
docker-compose up -d

# Deploy infrastructure (Makefile handles credentials automatically)
make deploy-localstack

# Or manually (ignore AWS credentials)
cd terraform
terraform init
AWS_ACCESS_KEY_ID= AWS_SECRET_ACCESS_KEY= AWS_SESSION_TOKEN= \
  AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
  terraform apply -var="environment=localstack" -auto-approve

# Test the pipeline
cd scripts
python test_pipeline.py --env localstack
```

### 2. AWS Learner Lab Deployment

```bash
# Ensure your AWS CLI is configured with Learner Lab credentials
aws sts get-caller-identity

# Deploy infrastructure (auto-detects LabRole)
make deploy-aws

# Test the pipeline
make test-aws

# Collect metrics
make metrics-aws
```

**Note:** The deployment automatically detects and uses the AWS Learner Lab LabRole. No manual configuration needed!

## Directory Structure

```
.
├── terraform/              # Infrastructure as Code (Modular)
│   ├── main.tf            # Root module - orchestrates resources
│   ├── variables.tf       # Variable definitions
│   ├── provider.tf        # Provider configuration
│   ├── outputs.tf         # Output definitions
│   ├── localstack.tfvars  # LocalStack settings
│   ├── aws.tfvars         # AWS Learner Lab settings
│   └── modules/           # Reusable modules
│       ├── s3/           # S3 bucket module
│       ├── lambda/       # Lambda function module
│       ├── dynamodb/     # DynamoDB table module
│       └── iam/          # IAM roles module
├── lambda/                # Lambda function code
│   ├── processor.py      # Main processing logic
│   └── requirements.txt
├── scripts/                    # Testing and metrics
│   ├── test_pipeline.py       # Quick pipeline test
│   ├── performance_test.py    # Performance benchmarks
│   ├── experiment_suite.py    # Comprehensive experiments (A-H)
│   ├── compare_experiments.py # Compare LocalStack vs AWS
│   ├── collect_metrics.py     # CloudWatch metrics
│   └── requirements.txt       # Python dependencies
├── test-data/            # Sample CSV files
└── README.md
```

## Lambda Processing Logic

1. **Fetch**: Retrieve CSV file from S3
2. **Schema Inference**: Detect column types (string, int, float, date)
3. **Statistics**: Compute row count, min/max/avg for numeric fields
4. **Quality Check**: Detect missing values, invalid data
5. **Output**: Generate summary JSON to `processed/`
6. **Metadata**: Write complete metadata to DynamoDB

## CloudWatch Metrics

### Lambda Metrics
- Duration (execution time)
- Invocations (count)
- Errors (failures)
- Throttles (rate limiting)
- ConcurrentExecutions (parallelism)

### DynamoDB Metrics
- SuccessfulRequestLatency
- ConsumedWriteCapacityUnits
- ThrottledRequests

### Derived Metrics
- Trigger delay (S3 upload → Lambda start)

## Testing

### Quick Test

Upload a sample CSV file and verify processing:

```bash
# The test script will:
# 1. Upload a CSV file to uploads/
# 2. Poll DynamoDB for processing completion
# 3. Verify the summary JSON in processed/
# 4. Display results and timing

python scripts/test_pipeline.py --env [localstack|aws]
```

### Comprehensive Experiments

Run comprehensive experiments to compare LocalStack vs AWS across multiple dimensions:

```bash
# Run all experiments on LocalStack (15-30 minutes)
make experiments-localstack

# Run all experiments on AWS (same scale, 30-45 minutes)
make experiments-aws

# Or run lightweight subset on AWS (5 minutes)
make experiments-aws-safe

# Compare results
make compare-experiments
```

**Available Experiments:**
- **A**: Deployment Speed - How fast can you deploy?
- **B**: End-to-End Pipeline Timing - Realistic latency measurement
- **D**: Failure Injection - Error handling behavior
- **F**: File Size Scaling - Performance vs file size
- **G**: Parallel Upload Scaling - Throughput vs parallelism
- **H**: IAM Policy Fidelity - Permission enforcement

📖 **Documentation:**
- [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) - Detailed guide with all experiments
- [EXPERIMENTS_QUICK_START.md](EXPERIMENTS_QUICK_START.md) - Quick reference for running experiments

**Key Findings:**
- LocalStack is 5-15× faster for development and CI/CD
- AWS shows realistic latency, throttling, and error behavior
- Use LocalStack for rapid iteration, AWS for validation

## Cleanup

```bash
cd terraform

# LocalStack
terraform destroy -var-file="localstack.tfvars" -auto-approve

# AWS
terraform destroy -var-file="aws.tfvars" -auto-approve

# Stop LocalStack container
docker stop localstack && docker rm localstack
```

## License

MIT

