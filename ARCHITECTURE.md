# Architecture Documentation

## Overview

This serverless data ingestion pipeline demonstrates event-driven architecture using AWS services (or LocalStack equivalents). It automatically processes CSV files uploaded to S3, extracting schema information, computing statistics, detecting quality issues, and storing metadata.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User / Application                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ 1. Upload CSV
                             ▼
                    ┌──────────────────┐
                    │   S3 Bucket      │
                    │   uploads/       │
                    └────────┬─────────┘
                             │
                             │ 2. S3 Event Notification
                             │    (ObjectCreated)
                             ▼
                    ┌──────────────────┐
                    │  Lambda Function │
                    │   Processor      │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                │ 3. Fetch CSV            │ 5. Write Metadata
                │    & Process            │
                │                         │
                ▼                         ▼
       ┌──────────────────┐    ┌──────────────────┐
       │   S3 Bucket      │    │   DynamoDB       │
       │   processed/     │    │   file_metadata  │
       └──────────────────┘    └──────────────────┘
         4. Upload Summary
            JSON
```

## Components

### 1. S3 Bucket

**Purpose**: Storage for incoming CSV files and processed results

**Prefixes**:
- `uploads/`: Incoming CSV files (trigger point)
- `processed/`: Generated summary JSON files

**Configuration**:
- Event notification on `ObjectCreated:*` events for `uploads/*.csv`
- Public access blocked
- Versioning disabled (can be enabled for production)

**Security**:
- Bucket policy restricts access to Lambda function
- No public read/write access
- Server-side encryption (can be enabled)

### 2. Lambda Function

**Purpose**: Process CSV files and extract insights

**Runtime**: Python 3.9  
**Memory**: 512 MB  
**Timeout**: 300 seconds (5 minutes)  

**Processing Steps**:

1. **Trigger**: Receives S3 event notification
2. **Fetch**: Downloads CSV file from S3
3. **Parse**: Reads CSV and extracts rows
4. **Schema Inference**: Determines data type for each column
   - `int`: Integer values
   - `float`: Floating-point numbers
   - `date`: Date strings (various formats)
   - `string`: Default type
5. **Statistics**: Computes min, max, average for numeric columns
6. **Quality Check**: Detects:
   - Missing values (empty cells)
   - Invalid values (type mismatches)
7. **Output**: Generates summary JSON and uploads to `processed/`
8. **Metadata**: Writes complete processing metadata to DynamoDB

**Error Handling**:
- Malformed files result in `status="error"` in DynamoDB
- Errors logged to CloudWatch
- Graceful degradation (partial results saved)

**Environment Variables**:
- `DYNAMODB_TABLE`: Name of metadata table
- `S3_BUCKET`: Name of data bucket
- `ENVIRONMENT`: Deployment environment (localstack/aws)

### 3. DynamoDB Table

**Purpose**: Store file processing metadata

**Table Name**: `data-ingestion-pipeline-file-metadata-{env}`  
**Partition Key**: `file_name` (String)  
**Billing Mode**: Pay-per-request (on-demand)

**Attributes**:
- `file_name` (S): Primary key
- `upload_timestamp` (S): ISO 8601 timestamp
- `processed_timestamp` (S): ISO 8601 timestamp
- `status` (S): "success" or "error"
- `row_count` (N): Number of rows processed
- `schema` (M): Map of column names to types
- `statistics` (M): Nested map of statistics per column
- `quality_issues` (M): Quality check results
- `error_message` (S): Error details (if status="error")

**Indexes**: None (can add GSI for query patterns)

**Example Item**:
```json
{
  "file_name": "sales_data.csv",
  "upload_timestamp": "2025-11-29T10:30:00Z",
  "processed_timestamp": "2025-11-29T10:30:15Z",
  "status": "success",
  "row_count": 100,
  "schema": {
    "name": "string",
    "age": "int",
    "salary": "float",
    "join_date": "date"
  },
  "statistics": {
    "age": {
      "min": 25,
      "max": 65,
      "avg": 42.5,
      "count": 100
    },
    "salary": {
      "min": 45000.00,
      "max": 150000.00,
      "avg": 75000.00,
      "count": 98
    }
  },
  "quality_issues": {
    "total_rows": 100,
    "has_issues": true,
    "missing_values": {
      "salary": {
        "count": 2,
        "percentage": 2.0
      }
    },
    "invalid_values": {}
  }
}
```

### 4. IAM Role

**Purpose**: Grant Lambda permissions to access AWS resources

**Trust Policy**: Allows Lambda service to assume role

**Permissions**:
- **CloudWatch Logs**:
  - `logs:CreateLogGroup`
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`

- **S3**:
  - `s3:GetObject` (read files from uploads/)
  - `s3:PutObject` (write files to processed/)
  - `s3:ListBucket` (list bucket contents)

- **DynamoDB**:
  - `dynamodb:PutItem` (write metadata)
  - `dynamodb:GetItem` (read metadata)
  - `dynamodb:UpdateItem` (update records)
  - `dynamodb:Query` (query by key)
  - `dynamodb:Scan` (full table scan)

**Note**: For AWS Learner Lab, uses existing LabRole instead of creating new role.

### 5. CloudWatch

**Purpose**: Monitoring and logging

**Log Groups**:
- `/aws/lambda/{function-name}`: Lambda execution logs
- Retention: 7 days (configurable)

**Metrics** (Automatic):

**Lambda**:
- `Duration`: Execution time in milliseconds
- `Invocations`: Number of invocations
- `Errors`: Number of failed invocations
- `Throttles`: Number of throttled requests
- `ConcurrentExecutions`: Number of concurrent executions

**DynamoDB**:
- `SuccessfulRequestLatency`: Request latency in milliseconds
- `ConsumedWriteCapacityUnits`: Write capacity consumed
- `UserErrors`: Client-side errors
- `SystemErrors`: Server-side errors

**S3**:
- `BucketSizeBytes`: Total bucket size
- `NumberOfObjects`: Number of objects

## Data Flow

### Happy Path

1. **Upload**: User uploads `data.csv` to `s3://bucket/uploads/data.csv`
2. **Trigger**: S3 sends event notification to Lambda
3. **Process**: Lambda:
   - Downloads `data.csv`
   - Parses CSV (10 rows, 4 columns)
   - Infers schema: `{name: string, age: int, salary: float, date: date}`
   - Computes statistics for numeric columns
   - Detects 2 missing values in salary column
   - Generates summary JSON
   - Uploads to `s3://bucket/processed/data_summary.json`
4. **Store**: Lambda writes metadata to DynamoDB with `status="success"`
5. **Complete**: Processing finishes in ~2 seconds

### Error Path

1. **Upload**: User uploads malformed CSV (invalid format)
2. **Trigger**: S3 sends event notification to Lambda
3. **Process**: Lambda:
   - Downloads file
   - Attempts to parse CSV
   - Encounters parsing error
   - Catches exception
4. **Store**: Lambda writes metadata to DynamoDB with:
   - `status="error"`
   - `error_message="CSV parsing failed: ..."`
   - `row_count=0`
   - Empty schema and statistics
5. **Log**: Error details logged to CloudWatch
6. **Complete**: Processing finishes gracefully

## Scalability

### Concurrent Processing

- **Lambda Concurrency**: 
  - Default: 1000 concurrent executions (AWS account limit)
  - Can process 1000 files simultaneously
  - LocalStack: Limited by local resources

- **DynamoDB**:
  - On-demand billing scales automatically
  - No capacity planning needed
  - Handles thousands of writes per second

- **S3**:
  - Virtually unlimited storage
  - Handles thousands of requests per second
  - No partitioning needed for this scale

### Performance Characteristics

**File Processing Time** (estimate):
- Small file (< 1 MB, 1K rows): ~1-2 seconds
- Medium file (10 MB, 10K rows): ~5-10 seconds
- Large file (100 MB, 100K rows): ~30-60 seconds

**Bottlenecks**:
1. Lambda timeout (5 minutes) - limits max file size
2. Lambda memory (512 MB) - affects parsing speed
3. Network latency (S3 download/upload)

**Optimization Opportunities**:
- Increase Lambda memory (up to 10 GB)
- Use streaming CSV parsing for large files
- Batch DynamoDB writes
- Enable S3 Transfer Acceleration

## Security Considerations

### Data Protection

1. **Encryption**:
   - S3: Can enable server-side encryption (SSE-S3 or SSE-KMS)
   - DynamoDB: Encryption at rest enabled by default
   - CloudWatch: Logs encrypted

2. **Access Control**:
   - Least privilege IAM policies
   - S3 bucket policies restrict access
   - No public endpoints

3. **Network**:
   - VPC endpoints for private connectivity (optional)
   - HTTPS for all API calls

### Compliance

- GDPR: PII detection can be added
- HIPAA: Encryption and audit logging supported
- SOC 2: CloudWatch provides audit trail

## Cost Analysis (AWS)

### Estimated Monthly Cost (1000 files/month, 1 MB each)

**Lambda**:
- Invocations: 1000 × $0.20/million = $0.20
- Duration: 1000 × 2s × $0.0000166667/GB-second × 0.5GB = $0.02
- **Total**: ~$0.22/month

**S3**:
- Storage: 2 GB × $0.023/GB = $0.05
- Requests: 2000 PUT + 1000 GET = $0.01
- **Total**: ~$0.06/month

**DynamoDB**:
- Storage: 1 GB × $0.25/GB = $0.25
- Writes: 1000 × $1.25/million = $0.00
- Reads: 100 × $0.25/million = $0.00
- **Total**: ~$0.25/month

**CloudWatch**:
- Logs: 1 GB × $0.50/GB = $0.50
- Metrics: Free (standard metrics)
- **Total**: ~$0.50/month

**GRAND TOTAL**: ~$1.03/month

**Note**: AWS Free Tier covers most of this for 12 months!

## LocalStack Differences

### Behavioral Differences

1. **Event Timing**: LocalStack may have delays in event propagation
2. **Metrics**: CloudWatch metrics may not populate in LocalStack
3. **IAM**: LocalStack uses simplified IAM (no actual authentication)
4. **Logs**: CloudWatch logs may be incomplete

### Feature Parity

**Supported**:
- ✅ S3 operations (put, get, list, notifications)
- ✅ Lambda invocation and execution
- ✅ DynamoDB operations (put, get, scan, query)
- ✅ IAM roles (basic)
- ✅ CloudWatch log groups

**Limited**:
- ⚠️ CloudWatch metrics (may not populate)
- ⚠️ S3 event notification timing
- ⚠️ Lambda concurrency limits

**Not Supported**:
- ❌ X-Ray tracing
- ❌ VPC configuration
- ❌ Advanced IAM policies

## Monitoring and Debugging

### CloudWatch Insights Queries

**Find all errors**:
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
```

**Calculate average processing time**:
```
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration) as avg_duration, max(@duration) as max_duration
```

**Find slow invocations**:
```
fields @timestamp, @duration, @message
| filter @type = "REPORT" and @duration > 5000
| sort @duration desc
```

### Useful AWS CLI Commands

**Tail Lambda logs**:
```bash
aws logs tail /aws/lambda/function-name --follow
```

**Get recent DynamoDB items**:
```bash
aws dynamodb scan --table-name table-name --limit 10
```

**List S3 objects**:
```bash
aws s3 ls s3://bucket-name/uploads/ --recursive
```

## Future Enhancements

1. **SNS Notifications**: Send alerts on processing errors
2. **SQS Integration**: Add queue for retry logic
3. **Step Functions**: Orchestrate multi-step workflows
4. **Athena**: Query processed data directly
5. **Glue Data Catalog**: Auto-register schemas
6. **EventBridge**: Advanced event routing
7. **Dead Letter Queue**: Handle failed invocations
8. **Provisioned Concurrency**: Reduce cold starts
9. **Lambda Layers**: Share common code
10. **CloudFormation**: Alternative to Terraform

