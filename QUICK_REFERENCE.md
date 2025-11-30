# Quick Reference Card

Fast lookup for common commands and operations.

## 🚀 Quick Start Commands

### LocalStack (Local Testing)
```bash
make localstack-up          # Start LocalStack
make deploy-localstack      # Deploy infrastructure
make test-localstack        # Run end-to-end test
make clean-localstack       # Clean up resources
```

### AWS Learner Lab (Production)
```bash
aws configure              # Configure credentials first
make deploy-aws            # Deploy infrastructure
make test-aws              # Run end-to-end test
make metrics-aws           # Collect CloudWatch metrics
make clean-aws             # Clean up resources
```

## 📁 File Locations

| What | Where |
|------|-------|
| **Infrastructure** | `terraform/*.tf` |
| **Lambda Code** | `lambda/processor.py` |
| **Test Scripts** | `scripts/*.py` |
| **Configuration** | `terraform/*.tfvars` |
| **Documentation** | `*.md` files |
| **Sample Data** | `test-data/sample.csv` |

## 🔧 Terraform Commands

```bash
cd terraform

# Initialize
terraform init

# Plan changes
terraform plan -var-file="localstack.tfvars"
terraform plan -var-file="aws.tfvars"

# Apply (deploy)
terraform apply -var-file="localstack.tfvars" -auto-approve
terraform apply -var-file="aws.tfvars" -var="lab_role_arn=arn:..." -auto-approve

# Destroy (cleanup)
terraform destroy -var-file="localstack.tfvars" -auto-approve
terraform destroy -var-file="aws.tfvars" -auto-approve

# Show current state
terraform show

# Get outputs
terraform output
terraform output -json
terraform output -raw s3_bucket_name
```

## 🧪 Testing Commands

```bash
cd scripts

# Run automated test
python3 test_pipeline.py --env localstack
python3 test_pipeline.py --env aws

# Test with custom file
python3 test_pipeline.py --env aws --file ../test-data/sample.csv

# Collect metrics
python3 collect_metrics.py --env aws --hours 1
python3 collect_metrics.py --env aws --hours 24 --output metrics.json
```

## 📊 AWS CLI Commands

### S3 Operations
```bash
# Get bucket name
BUCKET=$(cd terraform && terraform output -raw s3_bucket_name)

# List files
aws s3 ls s3://$BUCKET/uploads/
aws s3 ls s3://$BUCKET/processed/

# Upload file
aws s3 cp mydata.csv s3://$BUCKET/uploads/

# Download file
aws s3 cp s3://$BUCKET/processed/mydata_summary.json .

# For LocalStack, add: --endpoint-url=http://localhost:4566
```

### DynamoDB Operations
```bash
# Get table name
TABLE=$(cd terraform && terraform output -raw dynamodb_table_name)

# Scan table (list all items)
aws dynamodb scan --table-name $TABLE

# Get specific item
aws dynamodb get-item --table-name $TABLE \
  --key '{"file_name": {"S": "mydata.csv"}}'

# For LocalStack, add: --endpoint-url=http://localhost:4566
```

### Lambda Operations
```bash
# Get function name
LAMBDA=$(cd terraform && terraform output -raw lambda_function_name)

# List functions
aws lambda list-functions

# Get function details
aws lambda get-function --function-name $LAMBDA

# Invoke manually
aws lambda invoke --function-name $LAMBDA \
  --payload '{"test": "data"}' \
  response.json

# For LocalStack, add: --endpoint-url=http://localhost:4566
```

### CloudWatch Logs
```bash
# Tail logs (follow)
aws logs tail /aws/lambda/$LAMBDA --follow

# Tail logs (last 5 minutes)
aws logs tail /aws/lambda/$LAMBDA --since 5m

# Filter logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/$LAMBDA \
  --filter-pattern "ERROR"

# For LocalStack, add: --endpoint-url=http://localhost:4566
```

## 🐳 Docker Commands (LocalStack)

```bash
# Start LocalStack
docker-compose up -d

# Check status
docker ps
docker-compose ps

# View logs
docker logs data-ingestion-localstack
docker logs -f data-ingestion-localstack  # follow

# Stop LocalStack
docker-compose down

# Clean up everything
docker-compose down -v  # removes volumes too

# Restart
docker-compose restart
```

## 🔍 Debugging Commands

### Check Terraform State
```bash
cd terraform
terraform state list                    # List all resources
terraform state show aws_lambda_function.processor
terraform show | grep -A 10 "bucket"
```

### Check Lambda Execution
```bash
# Recent invocations
aws lambda get-function --function-name $LAMBDA \
  --query 'Configuration.LastModified'

# CloudWatch Insights query
aws logs tail /aws/lambda/$LAMBDA --format short
```

### Check S3 Event Notification
```bash
aws s3api get-bucket-notification-configuration \
  --bucket $BUCKET
```

### Check IAM Role
```bash
# Get role name
ROLE=$(cd terraform && terraform output -raw lambda_role_name 2>/dev/null || echo "LabRole")

# Get role details
aws iam get-role --role-name $ROLE

# Get role policies
aws iam list-role-policies --role-name $ROLE
aws iam get-role-policy --role-name $ROLE --policy-name lambda-policy
```

## 📈 Monitoring Queries

### CloudWatch Insights Queries

**Find all errors:**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
```

**Average processing time:**
```
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration) as avg_ms, max(@duration) as max_ms
```

**Slow invocations (> 5 seconds):**
```
fields @timestamp, @duration, @message
| filter @type = "REPORT" and @duration > 5000
| sort @duration desc
```

**Error rate:**
```
fields @timestamp
| filter @type = "REPORT"
| stats count() as invocations, 
        sum(@duration) as total_time,
        avg(@duration) as avg_time
```

## 🔑 Environment Variables

### For LocalStack
```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### For AWS Learner Lab
```bash
# From AWS Details page
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_SESSION_TOKEN=<your-token>
export AWS_DEFAULT_REGION=us-east-1
```

## 🎯 Common Workflows

### Deploy New Version
```bash
# 1. Edit lambda/processor.py
# 2. Redeploy
cd terraform
terraform apply -var-file="aws.tfvars" -auto-approve
# Lambda code is automatically re-packaged and updated
```

### Test Changes Locally
```bash
# 1. Make changes
# 2. Deploy to LocalStack
make deploy-localstack
# 3. Test
make test-localstack
# 4. If good, deploy to AWS
make deploy-aws
```

### Debug Processing Error
```bash
# 1. Check CloudWatch logs
aws logs tail /aws/lambda/$LAMBDA --since 10m

# 2. Check DynamoDB for error message
aws dynamodb get-item --table-name $TABLE \
  --key '{"file_name": {"S": "problematic.csv"}}'

# 3. Download original file
aws s3 cp s3://$BUCKET/uploads/problematic.csv .

# 4. Test locally (if needed)
```

### Monitor Performance
```bash
# 1. Run test load
for i in {1..10}; do
  python3 scripts/test_pipeline.py --env aws
  sleep 2
done

# 2. Wait for metrics (5-10 minutes)
sleep 600

# 3. Collect metrics
python3 scripts/collect_metrics.py --env aws --hours 1
```

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| **LocalStack not starting** | `docker-compose down && docker-compose up -d` |
| **Terraform state locked** | `terraform force-unlock <lock-id>` |
| **Lambda timeout** | Increase `lambda_timeout` in `variables.tf` |
| **Permission denied** | Check IAM role policies in `iam.tf` |
| **File not processed** | Check Lambda logs, S3 event notifications |
| **AWS credentials expired** | Restart Learner Lab session, re-configure |
| **Metrics not showing** | Wait 5-10 minutes, metrics have delay |
| **DynamoDB write error** | Check IAM permissions for Lambda role |

## 📝 Configuration Changes

### Change Lambda Memory
```hcl
# terraform/variables.tf
variable "lambda_memory" {
  default     = 1024  # Changed from 512
}
```

### Change Lambda Timeout
```hcl
# terraform/variables.tf
variable "lambda_timeout" {
  default     = 600  # Changed from 300 (10 minutes)
}
```

### Change DynamoDB Billing
```hcl
# terraform/dynamodb.tf
resource "aws_dynamodb_table" "file_metadata" {
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
}
```

### Add S3 Encryption
```hcl
# terraform/s3.tf
resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

## 📚 Documentation Quick Links

| Need to... | Read this... |
|------------|--------------|
| Get started quickly | `README.md` |
| Deploy the system | `DEPLOYMENT.md` |
| Run tests | `TESTING.md` |
| Understand architecture | `ARCHITECTURE.md` |
| See what was built | `PROJECT_SUMMARY.md` |
| Find files | `FILE_STRUCTURE.md` |
| Quick commands | `QUICK_REFERENCE.md` (this file) |

## 🎓 Learning Path

1. **Start here**: Read `README.md`
2. **Deploy locally**: Follow `DEPLOYMENT.md` LocalStack section
3. **Run tests**: Follow `TESTING.md` Test 1
4. **Understand system**: Read `ARCHITECTURE.md`
5. **Deploy to AWS**: Follow `DEPLOYMENT.md` AWS section
6. **Collect metrics**: Follow `TESTING.md` Test 6
7. **Customize**: Edit `lambda/processor.py` and `terraform/*.tf`

## 💡 Tips

- **Use Makefile** for common operations instead of typing long commands
- **Test in LocalStack first** before deploying to AWS
- **Check CloudWatch Logs** when debugging Lambda issues
- **Wait 5-10 minutes** for CloudWatch metrics to appear
- **Use terraform output** to get resource names dynamically
- **Keep Learner Lab session active** (AWS credentials expire)
- **Clean up resources** after testing to avoid charges
- **Version control** all `.tf` files and code

## 🆘 Getting Help

1. Check CloudWatch Logs for errors
2. Review `DEPLOYMENT.md` troubleshooting section
3. Review `TESTING.md` debug procedures
4. Run `terraform show` to see current state
5. Check DynamoDB for processing status
6. Verify S3 event notifications are configured

---

**Last Updated**: 2025-11-29  
**Version**: 1.0  
**Status**: Production Ready ✅

