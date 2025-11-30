# Deployment Guide

Complete deployment instructions for both LocalStack and AWS Learner Lab environments.

## Prerequisites

### Required Software

1. **Terraform** (>= 1.0)
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **AWS CLI** (>= 2.0)
   ```bash
   brew install awscli  # macOS
   # or download from https://aws.amazon.com/cli/
   ```

3. **Python 3.9+**
   ```bash
   python3 --version
   ```

4. **Docker Desktop** (for LocalStack)
   - Download from https://www.docker.com/products/docker-desktop

5. **Python Dependencies**
   ```bash
   pip3 install boto3
   ```

## Part 1: LocalStack Deployment

### Step 1: Start LocalStack

**Option A: Using Docker Compose (Recommended)**
```bash
# Start LocalStack
docker-compose up -d

# Verify it's running
docker ps
docker logs data-ingestion-localstack
```

**Option B: Using Docker Run**
```bash
docker run -d \
  --name localstack \
  -p 4566:4566 \
  -p 4510-4559:4510-4559 \
  -e SERVICES=s3,lambda,dynamodb,iam,sts,logs,cloudwatch \
  -e DEBUG=1 \
  localstack/localstack:latest
```

### Step 2: Configure AWS CLI for LocalStack

```bash
# Configure with dummy credentials
aws configure --profile localstack
# AWS Access Key ID: test
# AWS Secret Access Key: test
# Default region name: us-east-1
# Default output format: json

# Or export environment variables
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### Step 3: Deploy with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file="localstack.tfvars"

# Apply the configuration
terraform apply -var-file="localstack.tfvars" -auto-approve

# Save outputs
terraform output -json > ../outputs_localstack.json
```

### Step 4: Test the Pipeline

```bash
cd ../scripts

# Run the test script
python3 test_pipeline.py --env localstack

# Expected output:
# - File uploaded to S3
# - Lambda processes the file
# - Metadata written to DynamoDB
# - Summary JSON created in S3
```

### Step 5: Verify Resources

```bash
# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List Lambda functions
aws --endpoint-url=http://localhost:4566 lambda list-functions

# Scan DynamoDB table
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name $(terraform output -raw dynamodb_table_name)
```

---

## Part 2: AWS Learner Lab Deployment

### Step 1: Access AWS Learner Lab

1. Log in to AWS Learner Lab
2. Start the lab (wait for green indicator)
3. Click "AWS Details"
4. Copy the AWS CLI credentials

### Step 2: Configure AWS CLI

**Option A: Using AWS CLI Configure**
```bash
aws configure
# Paste Access Key ID
# Paste Secret Access Key
# Region: us-east-1
# Output: json
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_SESSION_TOKEN=<your-session-token>
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: AWS Credentials File**
```bash
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = <your-access-key>
aws_secret_access_key = <your-secret-key>
aws_session_token = <your-session-token>
EOF
```

### Step 3: Verify AWS Access

```bash
# Test AWS CLI access
aws sts get-caller-identity

# You should see your account ID and ARN
# Example output:
# {
#   "UserId": "AROAXXXXXXXXX:user",
#   "Account": "123456789012",
#   "Arn": "arn:aws:sts::123456789012:assumed-role/LabRole/user"
# }
```

### Step 4: Deploy with Terraform

**Using Makefile (Recommended - Auto-detects LabRole)**
```bash
# This automatically detects and uses the AWS Learner Lab LabRole
make deploy-aws

# The Makefile will:
# 1. Auto-detect the LabRole ARN if it exists
# 2. Use it for Lambda execution role
# 3. Or create a new role if LabRole is not found
```

**Manual Deployment (Advanced)**
```bash
cd terraform

# Initialize Terraform
terraform init

# Option A: Auto-detect LabRole
LAB_ROLE_ARN=$(aws iam list-roles --query 'Roles[?RoleName==`LabRole`].Arn' --output text)

if [ -n "$LAB_ROLE_ARN" ]; then
  echo "Using LabRole: $LAB_ROLE_ARN"
  terraform apply -var="environment=aws" -var="lab_role_arn=$LAB_ROLE_ARN" -auto-approve
else
  echo "Creating new Lambda execution role"
  terraform apply -var="environment=aws" -auto-approve
fi

# Save outputs
terraform output -json > ../outputs_aws.json
```

**Note:** The LabRole is automatically provided by AWS Learner Lab and has the necessary permissions for Lambda, S3, and DynamoDB.

### Step 5: Test the Pipeline

```bash
cd ../scripts

# Upload and test
python3 test_pipeline.py --env aws

# You can also upload your own CSV file
python3 test_pipeline.py --env aws --file ../test-data/sample.csv
```

### Step 6: Collect CloudWatch Metrics

```bash
# Wait a few minutes for metrics to propagate

# Collect metrics from the last hour
python3 collect_metrics.py --env aws --hours 1

# Collect metrics from the last 24 hours
python3 collect_metrics.py --env aws --hours 24 --output metrics_aws_24h.json
```

---

## Troubleshooting

### LocalStack Issues

**Lambda Not Triggered**
```bash
# Check Lambda logs
aws --endpoint-url=http://localhost:4566 logs tail \
  /aws/lambda/data-ingestion-pipeline-processor-localstack \
  --follow

# Check S3 event notifications
aws --endpoint-url=http://localhost:4566 s3api get-bucket-notification-configuration \
  --bucket $(terraform output -raw s3_bucket_name)
```

**DynamoDB Connection Issues**
```bash
# List tables
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# Describe table
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name $(terraform output -raw dynamodb_table_name)
```

### AWS Issues

**Permission Denied**
- Verify your AWS credentials are current (Learner Lab sessions expire)
- Check that the Lab Role has necessary permissions
- Restart the lab if needed

**Lambda Timeout**
- Check CloudWatch Logs: AWS Console > CloudWatch > Log groups
- Increase timeout in `terraform/variables.tf` if needed

**DynamoDB Throttling**
- Check consumed capacity in CloudWatch
- Consider increasing provisioned capacity (currently using on-demand)

### Common Terraform Issues

**State Lock**
```bash
# If terraform is stuck, you may need to force unlock
terraform force-unlock <lock-id>
```

**Resource Already Exists**
```bash
# Import existing resource
terraform import aws_s3_bucket.data_bucket <bucket-name>
```

**Destroy Issues**
```bash
# Force destroy (removes all objects)
terraform destroy -var-file="localstack.tfvars" -auto-approve
```

---

## Cleanup

### LocalStack Cleanup

```bash
# Destroy Terraform resources
cd terraform
terraform destroy -var-file="localstack.tfvars" -auto-approve

# Stop and remove container
docker-compose down

# Or with docker run
docker stop localstack
docker rm localstack

# Remove data (optional)
rm -rf localstack-data/
```

### AWS Cleanup

```bash
# Destroy Terraform resources
cd terraform
terraform destroy -var-file="aws.tfvars" -var="lab_role_arn=$LAB_ROLE_ARN" -auto-approve

# Verify all resources are deleted
aws s3 ls  # Should not show the pipeline bucket
aws lambda list-functions | grep data-ingestion
aws dynamodb list-tables | grep file-metadata
```

**IMPORTANT:** Always clean up AWS resources to avoid unnecessary charges or reaching resource limits in Learner Lab!

---

## Next Steps

After successful deployment:

1. **Run experiments**: Upload multiple CSV files with different characteristics
2. **Analyze metrics**: Compare LocalStack vs AWS performance
3. **Scale testing**: Upload files concurrently to test Lambda scalability
4. **Error handling**: Test with malformed CSV files
5. **Monitor costs**: Track AWS costs in Learner Lab (if applicable)

## Support

For issues or questions:
- Check CloudWatch Logs for Lambda execution details
- Review DynamoDB table contents
- Check S3 bucket for processed files
- Examine Terraform state: `terraform show`

