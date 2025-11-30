# Complete Workflow Diagrams

Visual guides for understanding and using the data ingestion pipeline.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER / APPLICATION                          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ 1. Upload CSV File
                             │    (employee_data.csv)
                             ▼
                    ┌──────────────────────┐
                    │     S3 Bucket        │
                    │   📦 uploads/        │◄─── Event Source
                    └──────────┬───────────┘
                               │
                               │ 2. S3 Event Notification
                               │    ObjectCreated:*.csv
                               ▼
                    ┌──────────────────────┐
                    │   Lambda Function    │
                    │   ⚡ processor       │
                    │                      │
                    │  • Fetch CSV         │
                    │  • Parse rows        │
                    │  • Infer schema      │
                    │  • Compute stats     │
                    │  • Check quality     │
                    └──────────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                │ 3. Upload Summary           │ 4. Write Metadata
                ▼                             ▼
       ┌──────────────────┐         ┌──────────────────┐
       │   S3 Bucket      │         │   DynamoDB       │
       │   📄 processed/  │         │   🗄️ Metadata    │
       │                  │         │                  │
       │ Summary JSON:    │         │ Record:          │
       │ • file_name      │         │ • file_name ⚡   │
       │ • schema         │         │ • schema         │
       │ • statistics     │         │ • statistics     │
       │ • quality issues │         │ • quality issues │
       │ • timestamps     │         │ • status         │
       └──────────────────┘         │ • timestamps     │
                                    └──────────────────┘
                │                             │
                └──────────────┬──────────────┘
                               │
                               │ 5. Logs & Metrics
                               ▼
                    ┌──────────────────────┐
                    │   CloudWatch         │
                    │   📊 Monitoring      │
                    │                      │
                    │  • Lambda logs       │
                    │  • Performance       │
                    │  • Error tracking    │
                    └──────────────────────┘
```

## Data Flow

```
CSV File Upload
      │
      ├─► S3 stores file in uploads/
      │   └─► Timestamp: T0
      │
      ├─► S3 triggers Lambda (via event notification)
      │   └─► Trigger delay: T1 - T0 (typically < 1 second)
      │
      ├─► Lambda processes file
      │   │
      │   ├─► Download from S3
      │   │   └─► Time: ~100-500ms
      │   │
      │   ├─► Parse CSV
      │   │   └─► Time: ~10-100ms per 1000 rows
      │   │
      │   ├─► Infer Schema
      │   │   │   ┌─► Integer detection
      │   │   │   ├─► Float detection
      │   │   │   ├─► Date detection
      │   │   │   └─► Default to string
      │   │   └─► Time: ~50-200ms
      │   │
      │   ├─► Compute Statistics
      │   │   │   ┌─► Min/Max/Avg for numeric columns
      │   │   │   └─► Count valid values
      │   │   └─► Time: ~50-200ms
      │   │
      │   ├─► Detect Quality Issues
      │   │   │   ┌─► Missing values (% and count)
      │   │   │   └─► Invalid values (type mismatches)
      │   │   └─► Time: ~50-200ms
      │   │
      │   ├─► Generate Summary JSON
      │   │   └─► Time: ~10ms
      │   │
      │   ├─► Upload to S3 processed/
      │   │   └─► Time: ~100-300ms
      │   │
      │   └─► Write to DynamoDB
      │       └─► Time: ~50-150ms
      │
      └─► Complete
          └─► Total time: T2 - T0 (typically 2-10 seconds)
```

## Processing Logic

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LAMBDA PROCESSOR FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

START
  │
  ├─► Receive S3 Event
  │   │
  │   ├─► Extract bucket name
  │   ├─► Extract object key
  │   └─► Extract timestamp
  │
  ├─► Validate Input
  │   │
  │   ├─► Is key in uploads/? ──NO──► Skip & Return 200
  │   └─► Is file .csv? ──────YES──► Continue
  │
  ├─► Download File from S3
  │   │
  │   └─► Error? ──YES──► Go to Error Handler
  │       └──NO──► Continue
  │
  ├─► Parse CSV
  │   │
  │   ├─► Read headers
  │   ├─► Read rows
  │   └─► Error? ──YES──► Go to Error Handler
  │       └──NO──► Continue
  │
  ├─► Infer Schema (for each column)
  │   │
  │   ├─► Try Integer ──SUCCESS──► Mark as 'int'
  │   ├─► Try Float ───SUCCESS──► Mark as 'float'
  │   ├─► Try Date ────SUCCESS──► Mark as 'date'
  │   └─► Default ─────────────► Mark as 'string'
  │
  ├─► Compute Statistics (for numeric columns)
  │   │
  │   ├─► Calculate min
  │   ├─► Calculate max
  │   ├─► Calculate avg
  │   └─► Count valid values
  │
  ├─► Detect Quality Issues
  │   │
  │   ├─► Count missing values (empty cells)
  │   ├─► Count invalid values (type mismatches)
  │   └─► Calculate percentages
  │
  ├─► Generate Summary JSON
  │   │
  │   ├─► file_name
  │   ├─► timestamps (upload, processed)
  │   ├─► row_count, column_count
  │   ├─► schema (column types)
  │   ├─► statistics (min/max/avg)
  │   └─► quality_issues (missing, invalid)
  │
  ├─► Upload Summary to S3 processed/
  │   │
  │   └─► Error? ──YES──► Log warning but continue
  │       └──NO──► Continue
  │
  ├─► Write Metadata to DynamoDB
  │   │
  │   ├─► Convert floats to Decimal
  │   ├─► Set status = "success"
  │   └─► Put item
  │
  └─► Return Success Response
      └─► statusCode: 200

ERROR HANDLER
  │
  ├─► Log error to CloudWatch
  │
  ├─► Create error record
  │   │
  │   ├─► file_name
  │   ├─► status = "error"
  │   ├─► error_message
  │   ├─► row_count = 0
  │   └─► empty schema/stats
  │
  ├─► Write to DynamoDB
  │
  └─► Return Success Response (graceful failure)
      └─► statusCode: 200
```

## Deployment Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOCALSTACK DEPLOYMENT                            │
└─────────────────────────────────────────────────────────────────────────┘

START
  │
  ├─► 1. Start LocalStack Container
  │   │   (docker-compose up -d)
  │   │
  │   ├─► Pull localstack/localstack:latest
  │   ├─► Start container on port 4566
  │   └─► Initialize services (S3, Lambda, DynamoDB, IAM, CloudWatch)
  │
  ├─► 2. Initialize Terraform
  │   │   (terraform init)
  │   │
  │   ├─► Download AWS provider
  │   └─► Initialize backend
  │
  ├─► 3. Apply Terraform Configuration
  │   │   (terraform apply -var-file="localstack.tfvars")
  │   │
  │   ├─► Create S3 bucket
  │   ├─► Package Lambda code (zip)
  │   ├─► Create Lambda function
  │   ├─► Create DynamoDB table
  │   ├─► Create IAM role (simplified)
  │   ├─► Configure S3 event notification
  │   └─► Create CloudWatch log group
  │
  ├─► 4. Test Deployment
  │   │   (python3 test_pipeline.py --env localstack)
  │   │
  │   ├─► Upload test CSV to S3
  │   ├─► Wait for Lambda execution
  │   ├─► Poll DynamoDB for result
  │   ├─► Verify summary JSON in S3
  │   └─► Display results
  │
  └─► COMPLETE ✅

┌─────────────────────────────────────────────────────────────────────────┐
│                       AWS LEARNER LAB DEPLOYMENT                         │
└─────────────────────────────────────────────────────────────────────────┘

START
  │
  ├─► 1. Configure AWS Credentials
  │   │   (aws configure)
  │   │
  │   ├─► Get credentials from Learner Lab
  │   ├─► Set AWS_ACCESS_KEY_ID
  │   ├─► Set AWS_SECRET_ACCESS_KEY
  │   ├─► Set AWS_SESSION_TOKEN
  │   └─► Verify: aws sts get-caller-identity
  │
  ├─► 2. Get Lab Role ARN
  │   │
  │   └─► Extract from caller identity or IAM console
  │
  ├─► 3. Initialize Terraform
  │   │   (terraform init)
  │   │
  │   ├─► Download AWS provider
  │   └─► Initialize backend
  │
  ├─► 4. Apply Terraform Configuration
  │   │   (terraform apply -var-file="aws.tfvars" -var="lab_role_arn=...")
  │   │
  │   ├─► Create S3 bucket
  │   ├─► Package Lambda code (zip)
  │   ├─► Create Lambda function (using LabRole)
  │   ├─► Create DynamoDB table
  │   ├─► Configure S3 event notification
  │   └─► Create CloudWatch log group
  │
  ├─► 5. Test Deployment
  │   │   (python3 test_pipeline.py --env aws)
  │   │
  │   ├─► Upload test CSV to S3
  │   ├─► Wait for Lambda execution
  │   ├─► Poll DynamoDB for result
  │   ├─► Verify summary JSON in S3
  │   └─► Display results
  │
  ├─► 6. Collect Metrics
  │   │   (wait 5-10 minutes)
  │   │   (python3 collect_metrics.py --env aws)
  │   │
  │   ├─► Query Lambda metrics
  │   ├─► Query DynamoDB metrics
  │   ├─► Calculate summaries
  │   └─► Export to JSON
  │
  └─► COMPLETE ✅
```

## Testing Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         END-TO-END TEST FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

START TEST
  │
  ├─► 1. Get Terraform Outputs
  │   │
  │   ├─► S3 bucket name
  │   ├─► DynamoDB table name
  │   └─► Lambda function name
  │
  ├─► 2. Generate or Load Test Data
  │   │
  │   ├─► Create sample CSV with:
  │   │   ├─► Valid data
  │   │   ├─► Missing values
  │   │   └─► Invalid values
  │   │
  │   └─► Generate unique filename with timestamp
  │
  ├─► 3. Upload to S3
  │   │
  │   ├─► PUT object to s3://bucket/uploads/test.csv
  │   ├─► Record upload timestamp
  │   └─► Print confirmation
  │
  ├─► 4. Poll DynamoDB (max 30 attempts, 2s delay)
  │   │
  │   ├─► Attempt 1 ──NOT FOUND──► Wait 2s
  │   ├─► Attempt 2 ──NOT FOUND──► Wait 2s
  │   ├─► ...
  │   └─► Attempt N ──FOUND─────► Continue
  │       └─── TIMEOUT ─────────► FAIL TEST
  │
  ├─► 5. Retrieve Metadata
  │   │
  │   ├─► Parse DynamoDB item
  │   └─► Check status field
  │       ├─► "success" ──► Continue
  │       └─► "error" ───► Display error but pass test
  │
  ├─► 6. Verify Summary JSON
  │   │
  │   ├─► Download from s3://bucket/processed/
  │   ├─► Parse JSON
  │   └─► Verify structure
  │
  ├─► 7. Calculate Metrics
  │   │
  │   ├─► Total processing time
  │   ├─► Upload → Lambda start delay
  │   └─► Lambda execution duration
  │
  ├─► 8. Display Results
  │   │
  │   ├─► File information
  │   ├─► Processing status
  │   ├─► Schema detected
  │   ├─► Statistics computed
  │   ├─► Quality issues found
  │   └─► Performance metrics
  │
  └─► TEST COMPLETE ✅

┌─────────────────────────────────────────────────────────────────────────┐
│                       METRICS COLLECTION FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

START COLLECTION
  │
  ├─► 1. Define Time Range
  │   │
  │   ├─► End time: Now
  │   └─► Start time: Now - N hours
  │
  ├─► 2. Collect Lambda Metrics
  │   │
  │   ├─► Duration (Average)
  │   ├─► Invocations (Sum)
  │   ├─► Errors (Sum)
  │   ├─► Throttles (Sum)
  │   └─► ConcurrentExecutions (Maximum)
  │
  ├─► 3. Collect DynamoDB Metrics
  │   │
  │   ├─► SuccessfulRequestLatency (Average)
  │   ├─► ConsumedWriteCapacityUnits (Sum)
  │   ├─► UserErrors (Sum)
  │   └─► SystemErrors (Sum)
  │
  ├─► 4. Calculate Summaries
  │   │
  │   ├─► Min, Max, Average for each metric
  │   └─► Total counts where applicable
  │
  ├─► 5. Display Results
  │   │
  │   ├─► Print to console (formatted tables)
  │   └─► Export to JSON file
  │
  └─► COLLECTION COMPLETE ✅
```

## Schema Inference Algorithm

```
For each column in CSV:
  │
  ├─► Collect all non-empty values
  │
  ├─► Try INTEGER
  │   │   For each value:
  │   │     Try: int(value)
  │   │   If all succeed ──► TYPE = 'int' ──► DONE
  │   │   If any fail ────► Continue
  │
  ├─► Try FLOAT
  │   │   For each value:
  │   │     Try: float(value)
  │   │   If all succeed ──► TYPE = 'float' ──► DONE
  │   │   If any fail ────► Continue
  │
  ├─► Try DATE
  │   │   For each format in [YYYY-MM-DD, MM/DD/YYYY, ...]:
  │   │     For first 10 values:
  │   │       Try: parse_date(value, format)
  │   │     If all succeed ──► TYPE = 'date' ──► DONE
  │   │     If any fail ────► Try next format
  │   │   If no format works ► Continue
  │
  └─► DEFAULT
      └─► TYPE = 'string' ──► DONE
```

## Quality Check Algorithm

```
For each column:
  │
  ├─► Check Missing Values
  │   │   Count = 0
  │   │   For each row:
  │   │     If cell is empty or whitespace only:
  │   │       Count += 1
  │   │   
  │   │   If Count > 0:
  │   │     Record: {count, percentage}
  │   │     Set has_issues = True
  │
  └─► Check Invalid Values (if column is int or float)
      │   Count = 0
      │   For each non-empty value:
      │     Try to convert to column type
      │     If conversion fails:
      │       Count += 1
      │   
      │   If Count > 0:
      │     Record: {count, percentage, expected_type}
      │     Set has_issues = True

Return: {
  total_rows,
  missing_values: {column: {count, percentage}},
  invalid_values: {column: {count, percentage, expected_type}},
  has_issues: boolean
}
```

## User Journey

```
Developer Setup:
  1. Clone repository
  2. Read README.md
  3. Install prerequisites (Terraform, AWS CLI, Python, Docker)
  4. Start LocalStack: make localstack-up
  5. Deploy: make deploy-localstack
  6. Test: make test-localstack
  7. Iterate on code, redeploy, test

Production Deployment:
  1. Access AWS Learner Lab
  2. Configure credentials: aws configure
  3. Deploy: make deploy-aws
  4. Test: make test-aws
  5. Monitor: make metrics-aws

Daily Usage:
  1. Upload CSV files to S3 uploads/
  2. Files are automatically processed
  3. Check DynamoDB for status
  4. Download summary JSON from S3 processed/
  5. Review CloudWatch logs if issues

Monitoring:
  1. Run: python3 collect_metrics.py --env aws
  2. Review metrics JSON
  3. Check CloudWatch dashboard
  4. Analyze performance trends
  5. Optimize if needed

Cleanup:
  1. LocalStack: make clean-localstack
  2. AWS: make clean-aws
  3. Stop LocalStack: docker-compose down
```

## State Transitions

```
File Upload → Processing → Complete/Error

States:
  UPLOADED ──Lambda Triggered──► PROCESSING
                                      │
                    ┌─────────────────┴────────────────┐
                    │                                  │
            Processing Success                Processing Error
                    │                                  │
                    ▼                                  ▼
       ┌─────────────────────┐            ┌─────────────────────┐
       │  DynamoDB Record    │            │  DynamoDB Record    │
       │  status="success"   │            │  status="error"     │
       │  + full metadata    │            │  + error_message    │
       └─────────────────────┘            └─────────────────────┘
                    │                                  │
                    │                                  │
                    ▼                                  ▼
       ┌─────────────────────┐            ┌─────────────────────┐
       │  S3 Summary JSON    │            │  No summary JSON    │
       │  in processed/      │            │  created            │
       └─────────────────────┘            └─────────────────────┘
```

---

**Navigation**:
- 📖 **Overview**: `README.md`
- 🚀 **Deploy**: `DEPLOYMENT.md`
- 🧪 **Test**: `TESTING.md`
- 🏗️ **Architecture**: `ARCHITECTURE.md`
- 📋 **Summary**: `PROJECT_SUMMARY.md`
- ⚡ **Quick Ref**: `QUICK_REFERENCE.md`
- 🔄 **Workflow**: This file

