# Serverless Event-Driven File Processing Pipeline
## LocalStack vs AWS Performance Comparison

A serverless data ingestion pipeline that processes CSV files with automatic schema inference, statistical analysis, and data quality validation. Runs identically on LocalStack (local) and AWS (production) for development-production parity and performance benchmarking.

---

## Architecture

```
CSV Upload → S3 (uploads/) → Lambda Processor → {
  - Infer schema (int, float, date, string)
  - Compute statistics (min, max, avg)
  - Detect quality issues
  - Generate summary JSON → S3 (processed/)
  - Write metadata → DynamoDB
}
```

**Components:**
- **S3 Bucket**: Input (`uploads/`) and output (`processed/`) storage
- **Lambda Function**: CSV processor with schema inference
- **DynamoDB Table**: File metadata storage
- **CloudWatch**: Metrics and logging

---

## Prerequisites

- Docker Desktop (for LocalStack)
- Python 3.9+
- Terraform 1.0+
- AWS CLI v2
- AWS Account (for AWS deployment)

---

## Quick Start

### LocalStack (Local)

```bash
make localstack-up          # Start LocalStack
make deploy-localstack      # Deploy infrastructure
make test-localstack        # Test pipeline
```

### AWS (Production)

```bash
aws sso login --profile your-profile
export AWS_PROFILE=your-profile
make deploy-aws            # Deploy infrastructure
make test-aws              # Test pipeline
```

---

## Project Structure

```
├── lambda/                     # Lambda function code
│   ├── processor.py           # CSV processing logic
│   └── requirements.txt
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                # Root module
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/               # S3, Lambda, DynamoDB, IAM
├── scripts/                    # Testing and analysis
│   ├── test_pipeline.py       # Quick test
│   ├── experiment_suite.py    # Experiments (A-H)
│   └── compare_experiments.py # Compare results
└── test-data/
    └── sample.csv
```

---

## Available Commands

```bash
# LocalStack
make localstack-up              # Start container
make deploy-localstack          # Deploy
make test-localstack            # Quick test
make experiments-localstack     # Run all experiments
make clean-localstack           # Destroy resources

# AWS
make deploy-aws                 # Deploy
make test-aws                   # Quick test
make experiments-aws-safe       # Safe experiments (B,D,H)
make experiments-aws            # Full experiments
make clean-aws                  # Destroy resources

# Analysis
make compare-experiments        # Compare LocalStack vs AWS
```

---

## Experiments

| ID | Name | Description |
|----|------|-------------|
| A | Deployment Speed | Infrastructure creation time |
| B | End-to-End Timing | Pipeline latency measurement |
| D | Failure Injection | Error handling behavior |
| F | File Size Scaling | Performance vs file size |
| G | Parallel Upload | Throughput vs concurrency |
| H | IAM Policy Fidelity | Permission enforcement |

**Run experiments:**
```bash
# LocalStack (15-30 min)
make experiments-localstack

# AWS lightweight (5 min)
make experiments-aws-safe

# Compare results
make compare-experiments
```

---

## Performance Results

| Metric | LocalStack | AWS | Difference |
|--------|-----------|-----|------------|
| Deployment Time | ~30s | ~120-180s | 4-6x faster |
| Cold Start | ~100ms | ~800-1500ms | 8-15x faster |
| Processing | ~50ms | ~200-500ms | 4-10x faster |
| Throughput (100 files) | ~50/min | ~30/min | 1.7x faster |

**Conclusion:** Use LocalStack for rapid development (5-15x faster), validate on AWS for production.

---

## Example Processing

**Input CSV** (`uploads/sales.csv`):
```csv
date,product,quantity,price
2025-01-01,Widget,10,29.99
2025-01-02,Gadget,5,49.99
2025-01-03,Widget,,39.99
```

**Output JSON** (`processed/sales_summary.json`):
```json
{
  "file_name": "sales.csv",
  "row_count": 3,
  "schema": {
    "date": "date",
    "product": "string",
    "quantity": "int",
    "price": "float"
  },
  "statistics": {
    "quantity": {"min": 5, "max": 10, "avg": 7.5},
    "price": {"min": 29.99, "max": 49.99, "avg": 39.99}
  },
  "quality_issues": {
    "missing_values": {
      "quantity": {"count": 1, "percentage": 33.33}
    }
  }
}
```

---

## Cleanup

```bash
# LocalStack
make clean-localstack

# AWS
make clean-aws
```

---

## License

MIT

