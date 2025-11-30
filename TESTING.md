# Testing Guide

Comprehensive testing instructions for validating the data ingestion pipeline.

## Quick Test

### LocalStack
```bash
# Start LocalStack and deploy
make localstack-up
make deploy-localstack

# Run test
make test-localstack
```

### AWS Learner Lab
```bash
# Configure AWS credentials first
aws configure

# Deploy
make deploy-aws

# Run test
make test-aws

# Collect metrics
make metrics-aws
```

## Detailed Testing

### Test 1: Happy Path - Valid CSV

**Objective**: Verify normal processing of a well-formed CSV file

**Steps**:
1. Upload sample CSV:
```bash
cd scripts
python3 test_pipeline.py --env [localstack|aws]
```

**Expected Results**:
- ✅ File uploaded to S3 `uploads/` prefix
- ✅ Lambda triggered automatically
- ✅ DynamoDB record created with `status="success"`
- ✅ Summary JSON created in S3 `processed/` prefix
- ✅ Schema inferred correctly
- ✅ Statistics computed for numeric columns
- ✅ Quality issues detected (if any)
- ✅ Processing completes in < 10 seconds

**Validation**:
```bash
# Check DynamoDB
aws dynamodb scan --table-name $(cd ../terraform && terraform output -raw dynamodb_table_name)

# Check S3 processed files
aws s3 ls s3://$(cd ../terraform && terraform output -raw s3_bucket_name)/processed/

# Check Lambda logs
aws logs tail /aws/lambda/$(cd ../terraform && terraform output -raw lambda_function_name) --follow
```

---

### Test 2: Data Quality Issues

**Objective**: Verify detection of missing and invalid values

**Steps**:
1. Create CSV with quality issues:
```csv
name,age,salary,join_date
Alice,30,75000.50,2022-01-15
Bob,invalid,65000.00,2022-03-20
Charlie,35,,2021-11-10
Diana,28,70000.00,invalid_date
```

2. Upload and process:
```bash
echo "name,age,salary,join_date
Alice,30,75000.50,2022-01-15
Bob,invalid,65000.00,2022-03-20
Charlie,35,,2021-11-10
Diana,28,70000.00,invalid_date" > /tmp/test_quality.csv

# Get bucket name
BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)

# Upload
aws s3 cp /tmp/test_quality.csv s3://$BUCKET/uploads/test_quality.csv
```

3. Wait and check results:
```bash
python3 test_pipeline.py --env aws --file /tmp/test_quality.csv
```

**Expected Results**:
- ✅ Processing succeeds (status="success")
- ✅ Missing values detected: `salary` column (1 missing, 25%)
- ✅ Invalid values detected: `age` column (1 invalid, 25%)
- ✅ Schema inferred despite issues
- ✅ Statistics computed excluding invalid/missing values

---

### Test 3: Error Handling - Malformed CSV

**Objective**: Verify graceful handling of unparseable files

**Steps**:
1. Create malformed CSV:
```bash
echo "This is not a valid CSV file
Just random text
No structure" > /tmp/test_malformed.txt

# Rename to .csv
mv /tmp/test_malformed.txt /tmp/test_malformed.csv

# Upload
BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)
aws s3 cp /tmp/test_malformed.csv s3://$BUCKET/uploads/test_malformed.csv
```

2. Check processing:
```bash
# Wait a few seconds
sleep 10

# Check DynamoDB
aws dynamodb get-item \
  --table-name $(cd ../terraform && terraform output -raw dynamodb_table_name) \
  --key '{"file_name": {"S": "test_malformed.csv"}}'
```

**Expected Results**:
- ✅ Lambda executes without crashing
- ✅ DynamoDB record created with `status="error"`
- ✅ `error_message` field populated with error details
- ✅ `row_count=0`
- ✅ Empty schema and statistics
- ✅ Error logged to CloudWatch

---

### Test 4: Large File Performance

**Objective**: Measure performance with larger files

**Steps**:
1. Generate large CSV:
```python
import csv
import random
from datetime import datetime, timedelta

# Generate 10,000 rows
with open('/tmp/test_large.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name', 'age', 'salary', 'join_date'])
    
    for i in range(10000):
        name = f"User_{i}"
        age = random.randint(20, 65)
        salary = random.uniform(40000, 150000)
        date = (datetime.now() - timedelta(days=random.randint(1, 1000))).strftime('%Y-%m-%d')
        writer.writerow([i, name, age, f"{salary:.2f}", date])

print("Generated test_large.csv with 10,000 rows")
```

2. Upload and measure:
```bash
# Start timer
START=$(date +%s)

# Upload
BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)
aws s3 cp /tmp/test_large.csv s3://$BUCKET/uploads/test_large.csv

# Wait for processing
python3 test_pipeline.py --env aws --file /tmp/test_large.csv

# End timer
END=$(date +%s)
echo "Total time: $((END - START)) seconds"
```

**Expected Results**:
- ✅ Processing completes successfully
- ✅ Duration < 60 seconds for 10K rows
- ✅ All 10,000 rows counted
- ✅ Statistics computed correctly
- ✅ No timeout errors

**Benchmarks** (approximate):
- 1K rows: ~2-5 seconds
- 10K rows: ~10-30 seconds  
- 100K rows: ~60-180 seconds

---

### Test 5: Concurrent Processing

**Objective**: Verify Lambda handles multiple simultaneous uploads

**Steps**:
1. Upload multiple files concurrently:
```bash
#!/bin/bash
BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)

# Upload 5 files simultaneously
for i in {1..5}; do
  (
    echo "name,age,salary
User$i,$(($i + 20)),$(($i * 10000))" > /tmp/test_concurrent_$i.csv
    
    aws s3 cp /tmp/test_concurrent_$i.csv s3://$BUCKET/uploads/test_concurrent_$i.csv
    echo "Uploaded file $i"
  ) &
done

# Wait for all uploads
wait
echo "All files uploaded"
```

2. Verify all processed:
```bash
# Wait for processing
sleep 15

# Check DynamoDB for all files
for i in {1..5}; do
  aws dynamodb get-item \
    --table-name $(cd ../terraform && terraform output -raw dynamodb_table_name) \
    --key "{\"file_name\": {\"S\": \"test_concurrent_$i.csv\"}}" \
    --query 'Item.status.S' \
    --output text
done
```

**Expected Results**:
- ✅ All 5 files processed successfully
- ✅ No throttling errors
- ✅ Each file has correct metadata in DynamoDB
- ✅ Each file has summary JSON in S3
- ✅ No Lambda concurrency errors

---

### Test 6: CloudWatch Metrics

**Objective**: Verify metrics are collected correctly

**Steps**:
1. Process several files:
```bash
# Upload 3-5 test files
for i in {1..3}; do
  python3 test_pipeline.py --env aws
  sleep 5
done
```

2. Wait for metrics to propagate (5-10 minutes)

3. Collect metrics:
```bash
# Collect from last hour
python3 collect_metrics.py --env aws --hours 1
```

**Expected Results**:
- ✅ Lambda metrics available:
  - Duration (milliseconds)
  - Invocations (count)
  - Errors (count = 0)
  - Throttles (count = 0)
- ✅ DynamoDB metrics available:
  - SuccessfulRequestLatency
  - ConsumedWriteCapacityUnits
  - No throttling
- ✅ Metrics exported to JSON file

**Note**: Metrics may take 5-15 minutes to appear in CloudWatch

---

### Test 7: Schema Inference Accuracy

**Objective**: Verify correct type detection

**Test Cases**:

| CSV Content | Expected Schema |
|-------------|----------------|
| `"123"` (all rows) | `int` |
| `"123.45"` (all rows) | `float` |
| `"2023-01-15"` (all rows) | `date` |
| `"Hello World"` | `string` |
| Mixed int and float | `float` |
| Mixed numeric and string | `string` |

**Steps**:
```bash
# Test integer detection
echo "id,count
1,100
2,200
3,300" | aws s3 cp - s3://$BUCKET/uploads/test_int.csv

# Test float detection
echo "id,price
1,19.99
2,29.99
3,39.99" | aws s3 cp - s3://$BUCKET/uploads/test_float.csv

# Test date detection
echo "id,date
1,2023-01-15
2,2023-02-20
3,2023-03-25" | aws s3 cp - s3://$BUCKET/uploads/test_date.csv
```

**Validation**:
Check DynamoDB `schema` field for each file

---

## Integration Tests

### End-to-End Test Script

Create `test_e2e.sh`:
```bash
#!/bin/bash
set -e

echo "=== End-to-End Integration Test ==="

ENV=${1:-localstack}
BUCKET=$(cd ../terraform && terraform output -raw s3_bucket_name)
TABLE=$(cd ../terraform && terraform output -raw dynamodb_table_name)

# Test 1: Upload valid CSV
echo "Test 1: Valid CSV"
echo "name,age,salary
Alice,30,75000" > /tmp/e2e_test.csv
python3 test_pipeline.py --env $ENV --file /tmp/e2e_test.csv
echo "✅ Test 1 passed"

# Test 2: Upload CSV with quality issues  
echo "Test 2: Quality Issues"
echo "name,age,salary
Bob,invalid,65000
Charlie,35," > /tmp/e2e_quality.csv
python3 test_pipeline.py --env $ENV --file /tmp/e2e_quality.csv
echo "✅ Test 2 passed"

# Test 3: Upload malformed file
echo "Test 3: Error Handling"
echo "Not a CSV" > /tmp/e2e_error.csv
aws s3 cp /tmp/e2e_error.csv s3://$BUCKET/uploads/e2e_error.csv
sleep 10
STATUS=$(aws dynamodb get-item --table-name $TABLE \
  --key '{"file_name": {"S": "e2e_error.csv"}}' \
  --query 'Item.status.S' --output text)
if [ "$STATUS" = "error" ]; then
  echo "✅ Test 3 passed"
else
  echo "❌ Test 3 failed: Expected error status"
  exit 1
fi

echo "=== All tests passed! ==="
```

Run:
```bash
chmod +x test_e2e.sh
./test_e2e.sh localstack  # or aws
```

---

## Performance Benchmarks

### LocalStack vs AWS Comparison

Run identical tests on both environments:

```bash
# LocalStack
make deploy-localstack
cd scripts
for i in {1..10}; do
  python3 test_pipeline.py --env localstack | grep "Total processing time"
done > localstack_times.txt

# AWS
make deploy-aws
for i in {1..10}; do
  python3 test_pipeline.py --env aws | grep "Total processing time"
done > aws_times.txt

# Compare
echo "LocalStack average:"
awk '{sum+=$4; count+=1} END {print sum/count}' localstack_times.txt

echo "AWS average:"
awk '{sum+=$4; count+=1} END {print sum/count}' aws_times.txt
```

**Expected Results**:
- AWS: Faster cold start, consistent timing
- LocalStack: May have longer initial latency, more variable

---

## Troubleshooting Tests

### Lambda Not Triggered

**Symptoms**: File uploaded but no DynamoDB record

**Debug Steps**:
```bash
# Check S3 event notification
aws s3api get-bucket-notification-configuration \
  --bucket $(cd ../terraform && terraform output -raw s3_bucket_name)

# Check Lambda permissions
aws lambda get-policy \
  --function-name $(cd ../terraform && terraform output -raw lambda_function_name)

# Check Lambda logs
aws logs tail /aws/lambda/$(cd ../terraform && terraform output -raw lambda_function_name) \
  --follow --since 5m
```

### Lambda Timeout

**Symptoms**: Processing takes > 5 minutes

**Debug Steps**:
```bash
# Check file size
aws s3 ls s3://$BUCKET/uploads/ --human-readable

# Increase timeout
# Edit terraform/variables.tf: lambda_timeout = 600
cd ../terraform
terraform apply -var-file="aws.tfvars" -auto-approve
```

### DynamoDB Write Failure

**Symptoms**: Lambda succeeds but no DynamoDB record

**Debug Steps**:
```bash
# Check IAM permissions
aws iam get-role-policy \
  --role-name $(cd ../terraform && terraform output -raw lambda_role_name) \
  --policy-name lambda-policy

# Check CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/$(terraform output -raw lambda_function_name) \
  --filter-pattern "ERROR"
```

---

## Test Checklist

Before considering the deployment complete:

- [ ] Valid CSV processed successfully
- [ ] Quality issues detected correctly  
- [ ] Error handling works (malformed files)
- [ ] Large files process without timeout
- [ ] Concurrent uploads handled
- [ ] CloudWatch metrics available
- [ ] Schema inference accurate
- [ ] Statistics computed correctly
- [ ] Summary JSON created in S3
- [ ] DynamoDB metadata complete
- [ ] Lambda logs accessible
- [ ] Both LocalStack and AWS work identically

---

## Continuous Testing

Set up a cron job to test regularly:

```bash
# Add to crontab (crontab -e)
0 * * * * cd /path/to/project/scripts && python3 test_pipeline.py --env aws >> /tmp/pipeline_test.log 2>&1
```

Or use AWS EventBridge (CloudWatch Events) for scheduled testing.

