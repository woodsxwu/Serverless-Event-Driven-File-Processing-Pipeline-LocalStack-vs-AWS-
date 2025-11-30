# Experiments Quick Start Guide

## TL;DR - Run Complete Comparison

```bash
# 1. Deploy both environments
make localstack-up
make deploy-localstack
make deploy-aws

# 2. Run experiments
make experiments-localstack     # ~20 minutes, all experiments
make experiments-aws            # ~30-45 minutes, all experiments

# 3. Compare results
make compare-experiments

# Result: Comprehensive comparison report showing LocalStack vs AWS across 8 dimensions
```

## Individual Experiments

### Experiment A: Deployment Speed
**Question:** How much faster is LocalStack deployment?

```bash
# LocalStack
cd scripts
python3 experiment_suite.py --env localstack --experiments A

# AWS  
python3 experiment_suite.py --env aws --experiments A
```

**Expected:** LocalStack 5-15× faster

---

### Experiment B: End-to-End Timing
**Question:** What's the realistic pipeline latency?

```bash
python3 experiment_suite.py --env localstack --experiments B
python3 experiment_suite.py --env aws --experiments B
```

**Expected:** LocalStack faster, but AWS shows real-world timing

---


### Experiment D: Error Handling
**Question:** Do errors behave the same way?

```bash
python3 experiment_suite.py --env localstack --experiments D
python3 experiment_suite.py --env aws --experiments D
```

**Expected:** Similar behavior, AWS has more detailed errors

---

### Experiment F: File Size Scaling
**Question:** How does performance scale with file size?

```bash
python3 experiment_suite.py --env localstack --experiments F  # up to 20K rows
python3 experiment_suite.py --env aws --experiments F          # up to 20K rows
```

**Expected:** AWS shows non-linear scaling, real bottlenecks

---

### Experiment G: Parallel Scaling  
**Question:** What's the maximum throughput?

```bash
python3 experiment_suite.py --env localstack --experiments G  # up to 100 parallel
python3 experiment_suite.py --env aws --experiments G          # up to 100 parallel
```

**Expected:** LocalStack unrealistic, AWS shows real limits

---

### Experiment H: IAM Fidelity
**Question:** Are permissions enforced correctly?

```bash
python3 experiment_suite.py --env localstack --experiments H
python3 experiment_suite.py --env aws --experiments H
```

**Expected:** LocalStack is permissive, AWS enforces strictly

---

## Test Scale

### Same Scale on Both Environments

All experiments run at **identical scale** on both LocalStack and AWS for fair comparison:

| Experiment | Scale | Notes |
|------------|-------|-------|
| A | 5 runs | Deployment timing |
| B | 20 files × 1000 rows | E2E pipeline |
| D | 6 test cases | Error handling |
| F | Up to 20K rows | File size scaling |
| G | Up to 100 parallel | Parallel scaling |
| H | 4 tests | IAM verification |

**AWS Considerations:**
- Estimated cost: $2-5 for full suite
- Time: 30-45 minutes
- ~200-500 Lambda invocations total

## Comparison Output

After running experiments on both environments:

```bash
make compare-experiments
```

You'll get:

```
📊 EXPERIMENT A: Deployment Speed
======================================================================
  Mean Time           LocalStack: 8.2s      AWS: 45.3s      5.5× faster

📊 EXPERIMENT B: End-to-End Pipeline Timing
======================================================================
  Upload Time:        0.032s / 0.045s       0.215s / 0.312s    6.7× faster
  Event Latency:      0.312s / 0.523s       2.145s / 3.782s    6.9× faster
  ...

📋 OVERALL SUMMARY & RECOMMENDATIONS
======================================================================
🎯 When to Use LocalStack:
   ✅ Rapid development and inner-loop testing
   ✅ CI/CD pipelines (faster feedback)
   ✅ Cost-free experimentation

🎯 When to Use AWS:
   ✅ Final integration testing
   ✅ Performance benchmarking
   ✅ IAM validation
```

## Troubleshooting

### LocalStack experiments hang
```bash
# Check LocalStack
docker ps | grep localstack

# Restart if needed
make localstack-down
make localstack-up
make deploy-localstack
```

### AWS rate limiting or throttling errors

**Cause:** High volume of requests to AWS services

**Solution:**
- This is expected! Throttling data is valuable for comparison
- The tests will continue and capture this behavior
- If completely blocked, wait 5-10 minutes between test runs

### No results to compare
```bash
# Check for results files
cd scripts
ls -lt experiments_*.json

# Re-run if needed
python3 experiment_suite.py --env localstack --experiments B C D
python3 experiment_suite.py --env aws --experiments B C D
```

## Best Practice Workflow

```
┌────────────────────────────────────────┐
│ 1. Develop with LocalStack            │
│    • Fast iteration                    │
│    • Unlimited testing                 │
└────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────┐
│ 2. Run Experiments on LocalStack      │
│    make experiments-localstack         │
│    (all 8 experiments)                 │
└────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────┐
│ 3. Validate on AWS                     │
│    make experiments-aws-safe           │
│    (experiments B, C, D, H only)       │
└────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────┐
│ 4. Compare & Analyze                   │
│    make compare-experiments            │
└────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────┐
│ 5. Deploy to Production with          │
│    confidence based on evidence        │
└────────────────────────────────────────┘
```

## Time Investment

| Activity | Time | Cost | Value |
|----------|------|------|-------|
| LocalStack experiments | 20 min | $0 | Complete baseline data |
| AWS experiments | 30-45 min | $2-5 | Real-world validation |
| Comparison analysis | 5 min | $0 | Evidence-based decisions |
| **Total** | **60-70 min** | **$2-5** | **Concrete proof with fair comparison** |

## Next Steps

1. **Run quick comparison:** Follow TL;DR section
2. **Read detailed guide:** See [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md)
3. **Customize experiments:** Modify `experiment_suite.py` for your needs
4. **Share results:** Use comparison report for team discussions

---

**Questions?** Check [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) for detailed documentation.

