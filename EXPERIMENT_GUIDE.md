# Comprehensive Experiment Guide: LocalStack vs AWS

This guide provides detailed instructions for running experiments that generate **concrete evidence** for comparing LocalStack and AWS across multiple dimensions.

## 📋 Table of Contents

- [Overview](#overview)
- [Safety Considerations](#safety-considerations)
- [Experiment Catalog](#experiment-catalog)
- [Quick Start](#quick-start)
- [Detailed Experiments](#detailed-experiments)
- [Comparison & Analysis](#comparison--analysis)
- [Best Practices](#best-practices)

## Overview

This experiment suite implements 6 comprehensive experiments (A, B, D, F, G, H) that provide quantitative evidence for:

| Dimension | LocalStack Advantage | AWS Advantage |
|-----------|---------------------|---------------|
| Development Speed | ✅ 5-15× faster deployment | - |
| CI/CD Integration | ✅ Fast feedback loops | - |
| Error Handling | ⚠️ Generic errors | ✅ Realistic errors |
| Performance Testing | ❌ Unrealistic (too fast) | ✅ Real latency |
| Concurrency/Scaling | ❌ No throttling | ✅ Real limits |
| IAM Enforcement | ⚠️ Partial enforcement | ✅ Full enforcement |
| Cost | ✅ Free | ❌ $$$ |

## Safety Considerations

### ⚠️ AWS Account Considerations

All experiments run at **the same scale** on both LocalStack and AWS for fair comparison. This ensures apples-to-apples metrics.

**What to expect:**
- All experiments (A-H) run identical workloads
- Same file counts, sizes, and parallelism levels
- True performance comparison

**AWS Costs & Quotas:**
- Lambda invocations: ~200-500 invocations per full test suite
- S3 operations: ~200-500 PUT/GET operations
- DynamoDB writes: ~200-500 items
- **Estimated cost**: $2-5 for complete test suite
- **Time required**: 30-45 minutes for all experiments

### Testing Configuration

The experiment suite uses the same limits for both environments:

```python
LOAD_LIMITS = {
    'localstack': {
        'max_concurrent_files': 100,
        'max_file_size_rows': 50000,
        'max_parallel_uploads': 100,
    },
    'aws': {
        'max_concurrent_files': 100,  # Same as LocalStack
        'max_file_size_rows': 50000,  # Same as LocalStack
        'max_parallel_uploads': 100,  # Same as LocalStack
    }
}
```

**Note:** If you're using AWS Learner Lab with strict quotas, you may want to reduce these limits in the code or run experiments individually.

## Experiment Catalog

### Experiment A: Deployment Speed
**What it measures:** Time to deploy infrastructure with Terraform
**Metric:** `T_deploy` (seconds)
**Expected outcome:** LocalStack 5-15× faster

### Experiment B: End-to-End Pipeline Timing
**What it measures:** Complete pipeline from upload → Lambda → DynamoDB
**Metrics:**
- `T_upload`: S3 upload time
- `T_event_latency`: Time from upload to Lambda invocation
- `T_processing`: Lambda execution time
- `T_total_pipeline`: Total end-to-end time

**Expected outcome:** LocalStack significantly faster, AWS shows realistic latency

### Experiment D: Failure Injection
**What it measures:** Error handling behavior
**Test cases:**
- Empty files
- Malformed CSV
- Missing values
- Oversized data

**Expected outcome:** AWS shows realistic errors, LocalStack may differ

### Experiment F: File Size Scaling
**What it measures:** Performance scaling with file size
**File sizes:** 100, 500, 1K, 5K, 10K, 50K rows
**Metrics:**
- Processing time
- Throughput (rows/sec)
- Success rate

**Expected outcome:** AWS shows non-linear scaling, LocalStack unrealistically fast

### Experiment G: Parallel Upload Scaling
**What it measures:** Scaling with parallelism
**Parallel levels:** 1, 5, 10, 20, 50, 100 files
**Metrics:**
- Throughput vs parallelism
- Scaling efficiency

**Expected outcome:** AWS shows throttling, LocalStack scales linearly

### Experiment H: IAM Policy Fidelity
**What it measures:** IAM policy enforcement
**Tests:**
- Lambda read/write permissions
- DynamoDB access
- Environment variables

**Expected outcome:** AWS enforces fully, LocalStack is permissive

## Quick Start

### Prerequisites

1. **LocalStack deployed:**
```bash
make localstack-up
make deploy-localstack
```

2. **AWS deployed (optional):**
```bash
aws configure  # Configure AWS credentials
make deploy-aws
```

### Run All Experiments (LocalStack)

```bash
cd scripts
python3 experiment_suite.py --env localstack
```

This will:
- Run all 8 experiments (A-H)
- Take approximately 10-20 minutes
- Generate `experiments_localstack_YYYYMMDD_HHMMSS.json`

### Run Experiments (AWS)

```bash
cd scripts
python3 experiment_suite.py --env aws
```

This runs all experiments on AWS at the same scale as LocalStack for fair comparison.

### Run Specific Experiments

```bash
# Only performance tests on LocalStack
python3 experiment_suite.py --env localstack --experiments E F G

# Only correctness tests on AWS
python3 experiment_suite.py --env aws --experiments B D H
```

### Compare Results

```bash
python3 compare_experiments.py \
  --localstack experiments_localstack_20251130_120000.json \
  --aws experiments_aws_20251130_120000.json
```

## Detailed Experiments

### Experiment A: Deployment Speed

**Objective:** Measure infrastructure deployment time

**LocalStack:**
```bash
cd scripts
python3 experiment_suite.py --env localstack --experiments A
```

Runs `terraform apply` 5 times and measures duration.

**AWS:**
```bash
python3 experiment_suite.py --env aws --experiments A
```

Runs `terraform plan` only (safer) 5 times.

**Expected Results:**
```
LocalStack: 5-15 seconds per apply
AWS:        30-60 seconds per plan
```

**What This Proves:** LocalStack is significantly faster for CI/CD pipelines.

---

### Experiment B: End-to-End Pipeline Timing

**Objective:** Measure realistic pipeline latency

```bash
# LocalStack: 20 files, 1000 rows each
python3 experiment_suite.py --env localstack --experiments B

# AWS: 20 files, 1000 rows each
python3 experiment_suite.py --env aws --experiments B
```

**Metrics Collected:**

| Metric | LocalStack (expected) | AWS (expected) |
|--------|-----------------------|----------------|
| T_upload | 0.01-0.05s | 0.1-0.3s |
| T_event_latency | 0.1-0.5s | 1-5s |
| T_processing | 0.5-2s | 0.5-2s |
| T_total_pipeline | 1-3s | 2-10s |

**What This Proves:**
- LocalStack is faster for development iteration
- AWS shows realistic S3 event notification delays
- Lambda processing time is similar (CPU-bound work)

---

### Experiment D: Failure Injection

**Objective:** Test error handling behavior

```bash
python3 experiment_suite.py --env localstack --experiments D
python3 experiment_suite.py --env aws --experiments D
```

**Test Cases:**

| Test Case | Expected Behavior |
|-----------|-------------------|
| Empty file | Error status in DynamoDB |
| No header | Error or minimal processing |
| Malformed CSV | Error with parsing details |
| Single column | Success with basic schema |
| All missing values | Success with quality issues flagged |
| Oversized row | Success (handle large fields) |

**What This Proves:**
- Error handling works in both environments
- AWS may provide more detailed error messages
- LocalStack may be more permissive

---

### Experiment F: File Size Scaling

**Objective:** Measure performance vs file size

```bash
# LocalStack: up to 20K rows
python3 experiment_suite.py --env localstack --experiments F

# AWS: up to 5K rows (safe)
python3 experiment_suite.py --env aws --experiments F
```

**File Sizes Tested:**
- Both environments: 100, 500, 1K, 5K, 10K, 20K rows

**Expected Results:**

| Rows | LocalStack Time | AWS Time | AWS Throughput |
|------|----------------|----------|----------------|
| 100 | 0.5s | 1.5s | 66 rows/sec |
| 1000 | 1.5s | 4s | 250 rows/sec |
| 5000 | 5s | 15s | 333 rows/sec |

**What This Proves:**
- AWS shows realistic processing time
- Non-linear scaling may indicate bottlenecks
- LocalStack is unrealistically fast

---

### Experiment G: Parallel Upload Scaling

**Objective:** Measure throughput vs parallelism

```bash
# LocalStack: 1, 5, 10, 20, 50, 100 parallel
python3 experiment_suite.py --env localstack --experiments G

# AWS: 1, 2, 5, 10 parallel (safe)
python3 experiment_suite.py --env aws --experiments G
```

**What It Measures:**
- How throughput scales with parallelism
- Where throttling begins
- Concurrency limits

**Expected Results:**
```
LocalStack:
  - Nearly linear scaling up to 100
  - No throttling
  
AWS:
  - Linear up to 10-20
  - May throttle at higher levels
  - Shows Lambda concurrency limits
```

**What This Proves:** AWS is necessary for testing real-world concurrency and throttling behavior.

---

### Experiment H: IAM Policy Fidelity

**Objective:** Verify IAM enforcement

```bash
python3 experiment_suite.py --env localstack --experiments H
python3 experiment_suite.py --env aws --experiments H
```

**Tests (observational only):**
1. Lambda can read from `uploads/`
2. Lambda can write to `processed/`
3. Lambda can write to DynamoDB
4. Environment variables configured

**Note:** This test does NOT modify IAM policies. It only verifies current permissions work correctly.

**What This Proves:**
- Basic permissions work in both
- LocalStack's IAM is simplified
- Full IAM validation requires AWS

---

## Comparison & Analysis

### Generate Comparison Report

After running experiments on both environments:

```bash
python3 compare_experiments.py \
  --localstack experiments_localstack_20251130_120000.json \
  --aws experiments_aws_20251130_120000.json
```

Output:
```
📊 EXPERIMENT A: Deployment Speed
======================================================================
  Mean Time           LocalStack: 8.2s      AWS: 45.3s      5.5× faster

📊 EXPERIMENT B: End-to-End Pipeline Timing
======================================================================
  Upload Time:        0.032s / 0.045s       0.215s / 0.312s    6.7× faster
  Event Latency:      0.312s / 0.523s       2.145s / 3.782s    6.9× faster
  Processing Time:    1.245s / 1.523s       1.312s / 1.678s    1.1× faster
  Total Pipeline:     1.589s / 2.091s       3.672s / 5.772s    2.3× faster

📊 EXPERIMENT C: Event Trigger Reliability
======================================================================
  Trigger Reliability:   96.0%                100.0%           +4.0%
  Success Rate:          95.0%                100.0%           +5.0%
```

### Save Report to File

```bash
python3 compare_experiments.py \
  --localstack experiments_localstack_20251130_120000.json \
  --aws experiments_aws_20251130_120000.json \
  --output comparison_report_20251130.txt
```

## Best Practices

### Development Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOCAL DEVELOPMENT (LocalStack)                          │
│    • Rapid iteration                                        │
│    • Test basic functionality                               │
│    • Debug issues quickly                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CI/CD TESTING (LocalStack)                              │
│    • Run full test suite                                    │
│    • Validate changes                                       │
│    • Fast feedback (< 5 minutes)                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. STAGING VALIDATION (AWS Learner Lab)                    │
│    • Run Experiments B, C, D, H                            │
│    • Validate triggers and errors                           │
│    • Verify IAM policies                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PERFORMANCE TESTING (AWS Production/Staging)            │
│    • Run Experiments E, F, G                                │
│    • Capacity planning                                      │
│    • Load testing                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. PRODUCTION DEPLOYMENT (AWS Production)                  │
│    • Deploy with confidence                                 │
│    • Monitor performance                                    │
└─────────────────────────────────────────────────────────────┘
```

### When to Use Each Environment

| Task | LocalStack | AWS Learner Lab | AWS Production |
|------|------------|-----------------|----------------|
| Feature development | ✅ Primary | ❌ | ❌ |
| Unit testing | ✅ Primary | ❌ | ❌ |
| Integration testing | ✅ Primary | ✅ Validation | ❌ |
| CI/CD testing | ✅ Primary | ⚠️ Limited | ❌ |
| Trigger validation | ⚠️ Good | ✅ Essential | ✅ Final |
| Error testing | ✅ Good | ✅ Validation | ✅ Final |
| IAM testing | ⚠️ Basic | ✅ Essential | ✅ Final |
| Performance testing | ❌ | ⚠️ Limited | ✅ Essential |
| Load testing | ❌ | ❌ Risky | ✅ Essential |
| Capacity planning | ❌ | ❌ | ✅ Essential |

### Cost Optimization

**LocalStack (Free):**
- Unlimited experiments
- No time constraints
- Run heavy load tests

**AWS Learner Lab ($$$):**
- Limited by quotas
- Run only necessary tests
- Focus on correctness, not load

**Estimated Costs:**

| Activity | LocalStack | AWS Learner Lab |
|----------|------------|-----------------|
| 100 experiments/day | $0 | ~$2-5/day |
| Load testing | $0 | ⚠️ Risk of blocking |
| CI/CD (per build) | $0 | ~$0.10-0.50 |

**Savings with LocalStack:** ~$50-100/month for active development

## Troubleshooting

### Experiment Suite Hangs

**Problem:** Tests timeout waiting for processing

**Solution:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/$(cd ../terraform && terraform output -raw lambda_function_name) --follow

# Check if LocalStack is running
docker ps | grep localstack

# Restart LocalStack
make localstack-down
make localstack-up
make deploy-localstack
```

### AWS Account Blocked

**Problem:** "Your account has been temporarily suspended"

**Cause:** Running too many requests or large load tests

**Solution:**
- Wait for cooldown period (usually 30-60 minutes)
- Use LocalStack for load testing
- Always stay within safe limits for AWS

### Comparison Script Fails

**Problem:** `compare_experiments.py` shows "Incomplete data"

**Cause:** Different experiments run on each environment

**Solution:**
```bash
# Run same experiments on both
python3 experiment_suite.py --env localstack --experiments B C D H
python3 experiment_suite.py --env aws --experiments B C D H

# Then compare
python3 compare_experiments.py --localstack experiments_localstack_*.json --aws experiments_aws_*.json
```

## Example: Complete Comparison Run

```bash
#!/bin/bash
# Complete LocalStack vs AWS comparison

set -e

echo "🚀 Starting LocalStack vs AWS Comparison"

# 1. Run LocalStack experiments (all)
echo "📊 Running LocalStack experiments..."
cd scripts
python3 experiment_suite.py --env localstack
LS_RESULTS=$(ls -t experiments_localstack_*.json | head -1)
echo "✅ LocalStack results: $LS_RESULTS"

# 2. Run AWS experiments (safe only)
echo "📊 Running AWS experiments (safe subset)..."
python3 experiment_suite.py --env aws --experiments B C D H
AWS_RESULTS=$(ls -t experiments_aws_*.json | head -1)
echo "✅ AWS results: $AWS_RESULTS"

# 3. Generate comparison
echo "📊 Generating comparison report..."
python3 compare_experiments.py \
  --localstack "$LS_RESULTS" \
  --aws "$AWS_RESULTS" \
  --output "comparison_$(date +%Y%m%d_%H%M%S).txt"

echo "✅ Comparison complete!"
```

## References

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

**Questions or Issues?** Check the main [README.md](README.md) or [TESTING.md](TESTING.md)

