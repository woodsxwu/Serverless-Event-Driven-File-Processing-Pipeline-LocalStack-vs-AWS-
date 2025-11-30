#!/usr/bin/env python3
"""
Compare performance results between LocalStack and AWS.
Generates comprehensive analysis and recommendations.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import argparse

class EnvironmentComparison:
    def __init__(self, localstack_file: str, aws_file: str = None):
        self.localstack_data = self._load_json(localstack_file)
        self.aws_data = self._load_json(aws_file) if aws_file else None
        
    def _load_json(self, filepath: str) -> Dict:
        """Load JSON data from file."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {filepath}: {e}")
            return None
    
    def _print_header(self, title: str):
        """Print section header."""
        print(f"\n{'='*80}")
        print(f"{title:^80}")
        print(f"{'='*80}\n")
    
    def _print_metrics_comparison(self, test_name: str, localstack_metrics: Dict, aws_metrics: Dict = None):
        """Print side-by-side comparison of metrics."""
        print(f"\n📊 {test_name}")
        print("-" * 80)
        
        if aws_metrics:
            print(f"{'Metric':<30} {'LocalStack':>20} {'AWS':>20} {'Difference':>20}")
            print("-" * 80)
        else:
            print(f"{'Metric':<30} {'LocalStack':>20}")
            print("-" * 80)
        
        for key, value in localstack_metrics.items():
            if isinstance(value, dict):
                continue  # Skip nested dicts for now
            
            ls_val = value
            if aws_metrics and key in aws_metrics:
                aws_val = aws_metrics[key]
                
                # Calculate difference
                if isinstance(ls_val, (int, float)) and isinstance(aws_val, (int, float)):
                    if aws_val != 0:
                        diff_pct = ((ls_val - aws_val) / aws_val) * 100
                        diff_str = f"{diff_pct:+.1f}%"
                        if diff_pct > 10:
                            diff_str = f"🔴 {diff_str}"
                        elif diff_pct < -10:
                            diff_str = f"🟢 {diff_str}"
                        else:
                            diff_str = f"🟡 {diff_str}"
                    else:
                        diff_str = "N/A"
                    
                    print(f"{key:<30} {ls_val:>20} {aws_val:>20} {diff_str:>20}")
                else:
                    print(f"{key:<30} {str(ls_val):>20} {str(aws_val):>20}")
            else:
                print(f"{key:<30} {str(ls_val):>20}")
    
    def compare_latency(self):
        """Compare single file latency tests."""
        self._print_header("LATENCY COMPARISON")
        
        ls_test = self.localstack_data.get('tests', {}).get('single_file_latency', {})
        aws_test = self.aws_data.get('tests', {}).get('single_file_latency', {}) if self.aws_data else {}
        
        print(f"Test Configuration:")
        print(f"  • Number of runs: {ls_test.get('num_runs', 'N/A')}")
        print(f"  • Rows per file: {ls_test.get('rows_per_file', 'N/A')}")
        
        # Processing time comparison
        ls_proc = ls_test.get('processing_time', {})
        aws_proc = aws_test.get('processing_time', {}) if aws_test else None
        
        if aws_proc:
            print(f"\n⏱️  Processing Time:")
            print(f"{'':30} {'LocalStack':>20} {'AWS':>20} {'Difference':>20}")
            print("-" * 80)
            
            for metric in ['min', 'mean', 'median', 'max', 'stdev']:
                if metric in ls_proc:
                    ls_val = ls_proc[metric]
                    aws_val = aws_proc.get(metric, 0)
                    
                    if aws_val != 0:
                        diff_pct = ((ls_val - aws_val) / aws_val) * 100
                        emoji = "🟢" if diff_pct < 0 else "🔴"
                        diff_str = f"{emoji} {diff_pct:+.1f}%"
                    else:
                        diff_str = "N/A"
                    
                    print(f"{metric.capitalize():<30} {ls_val:>18.3f}s {aws_val:>18.3f}s {diff_str:>20}")
        else:
            print(f"\n⏱️  Processing Time (LocalStack only):")
            for metric, value in ls_proc.items():
                if metric != 'count':
                    print(f"  • {metric.capitalize()}: {value:.3f}s")
        
        # Total time comparison
        ls_total = ls_test.get('total_time', {})
        aws_total = aws_test.get('total_time', {}) if aws_test else None
        
        if aws_total:
            print(f"\n⏱️  Total Time (Upload + Processing):")
            print(f"{'':30} {'LocalStack':>20} {'AWS':>20} {'Difference':>20}")
            print("-" * 80)
            
            for metric in ['min', 'mean', 'median', 'max']:
                if metric in ls_total:
                    ls_val = ls_total[metric]
                    aws_val = aws_total.get(metric, 0)
                    
                    if aws_val != 0:
                        diff_pct = ((ls_val - aws_val) / aws_val) * 100
                        emoji = "🟢" if diff_pct < 0 else "🔴"
                        diff_str = f"{emoji} {diff_pct:+.1f}%"
                    else:
                        diff_str = "N/A"
                    
                    print(f"{metric.capitalize():<30} {ls_val:>18.3f}s {aws_val:>18.3f}s {diff_str:>20}")
        else:
            print(f"\n⏱️  Total Time (LocalStack only):")
            for metric, value in ls_total.items():
                if metric != 'count':
                    print(f"  • {metric.capitalize()}: {value:.3f}s")
    
    def compare_throughput(self):
        """Compare concurrent processing throughput."""
        self._print_header("THROUGHPUT COMPARISON")
        
        ls_test = self.localstack_data.get('tests', {}).get('concurrent_processing', {})
        aws_test = self.aws_data.get('tests', {}).get('concurrent_processing', {}) if self.aws_data else {}
        
        print(f"Test Configuration:")
        print(f"  • Number of files: {ls_test.get('num_files', 'N/A')}")
        print(f"  • Rows per file: {ls_test.get('rows_per_file', 'N/A')}")
        
        print(f"\n📈 Upload Performance:")
        ls_up_throughput = ls_test.get('upload_throughput', 0)
        aws_up_throughput = aws_test.get('upload_throughput', 0) if aws_test else 0
        
        if aws_up_throughput > 0:
            diff = ((ls_up_throughput - aws_up_throughput) / aws_up_throughput) * 100
            emoji = "🟢" if diff > 0 else "🔴"
            print(f"  • LocalStack: {ls_up_throughput:.2f} files/sec")
            print(f"  • AWS:        {aws_up_throughput:.2f} files/sec")
            print(f"  • Difference: {emoji} {diff:+.1f}%")
        else:
            print(f"  • LocalStack: {ls_up_throughput:.2f} files/sec")
        
        print(f"\n📈 Processing Throughput:")
        ls_proc_throughput = ls_test.get('processing_throughput', 0)
        aws_proc_throughput = aws_test.get('processing_throughput', 0) if aws_test else 0
        
        if aws_proc_throughput > 0:
            diff = ((ls_proc_throughput - aws_proc_throughput) / aws_proc_throughput) * 100
            emoji = "🟢" if diff > 0 else "🔴"
            print(f"  • LocalStack: {ls_proc_throughput:.2f} files/sec")
            print(f"  • AWS:        {aws_proc_throughput:.2f} files/sec")
            print(f"  • Difference: {emoji} {diff:+.1f}%")
        else:
            print(f"  • LocalStack: {ls_proc_throughput:.2f} files/sec")
        
        print(f"\n✅ Success Rate:")
        ls_success = ls_test.get('successful_processing', 0) / ls_test.get('num_files', 1) * 100
        print(f"  • LocalStack: {ls_success:.1f}%")
        
        if aws_test:
            aws_success = aws_test.get('successful_processing', 0) / aws_test.get('num_files', 1) * 100
            print(f"  • AWS:        {aws_success:.1f}%")
    
    def compare_scalability(self):
        """Compare large file handling."""
        self._print_header("SCALABILITY COMPARISON")
        
        ls_tests = self.localstack_data.get('tests', {}).get('large_file_handling', [])
        aws_tests = self.aws_data.get('tests', {}).get('large_file_handling', []) if self.aws_data else []
        
        print(f"{'File Size':<15} {'LocalStack':^30} {'AWS':^30}")
        print(f"{'(rows)':<15} {'Processing':>15} {'Throughput':>15} {'Processing':>15} {'Throughput':>15}")
        print("-" * 80)
        
        for ls_test in ls_tests:
            if not ls_test.get('success'):
                continue
            
            rows = ls_test['rows']
            ls_time = ls_test['processing_time']
            ls_throughput = ls_test['throughput']
            
            # Find matching AWS test
            aws_test = next((t for t in aws_tests if t.get('rows') == rows and t.get('success')), None)
            
            if aws_test:
                aws_time = aws_test['processing_time']
                aws_throughput = aws_test['throughput']
                print(f"{rows:<15} {ls_time:>13.2f}s {ls_throughput:>13.1f}r/s {aws_time:>13.2f}s {aws_throughput:>13.1f}r/s")
            else:
                print(f"{rows:<15} {ls_time:>13.2f}s {ls_throughput:>13.1f}r/s {'N/A':>13} {'N/A':>15}")
    
    def generate_recommendations(self):
        """Generate recommendations based on test results."""
        self._print_header("RECOMMENDATIONS")
        
        ls_test = self.localstack_data.get('tests', {})
        
        print("🎯 When to Use LocalStack:")
        print("  ✓ Development and testing")
        print("  ✓ CI/CD pipelines")
        print("  ✓ Cost-free experimentation")
        print("  ✓ Offline development")
        print("  ✓ Rapid prototyping")
        
        latency = ls_test.get('single_file_latency', {}).get('processing_time', {})
        if latency.get('mean', 0) < 5:
            print("  ✓ Fast iteration cycles (low latency observed)")
        
        print("\n🎯 When to Use AWS:")
        print("  ✓ Production workloads")
        print("  ✓ Real CloudWatch metrics and monitoring")
        print("  ✓ Integration with other AWS services")
        print("  ✓ Production-grade durability and availability")
        print("  ✓ Real-world performance characteristics")
        
        if self.aws_data:
            aws_latency = self.aws_data.get('tests', {}).get('single_file_latency', {}).get('processing_time', {})
            if aws_latency.get('mean', 0) > latency.get('mean', 0):
                print("  ✓ Performance testing that matches production")
        
        print("\n⚠️  Key Differences:")
        print("  • LocalStack: Limited CloudWatch metrics (most are empty)")
        print("  • LocalStack: Faster cold starts (no real Lambda initialization)")
        print("  • LocalStack: No real network latency")
        print("  • LocalStack: Simplified service behaviors")
        print("  • AWS: Real costs, quotas, and limits")
        print("  • AWS: Full observability and monitoring")
        print("  • AWS: Production-grade durability guarantees")
        
        print("\n💡 Best Practices:")
        print("  1. Develop and test with LocalStack")
        print("  2. Run performance tests on AWS before production")
        print("  3. Use LocalStack for CI/CD to save costs")
        print("  4. Validate critical paths on real AWS")
        print("  5. Monitor actual CloudWatch metrics in AWS")
    
    def estimate_costs(self):
        """Estimate AWS costs vs LocalStack."""
        self._print_header("COST ANALYSIS")
        
        ls_test = self.localstack_data.get('tests', {}).get('concurrent_processing', {})
        num_files = ls_test.get('num_files', 0)
        
        # AWS pricing (us-west-2, approximate)
        lambda_cost_per_million = 0.20  # $0.20 per 1M requests
        lambda_duration_cost = 0.0000166667  # per GB-second
        s3_put_cost_per_1000 = 0.005  # $0.005 per 1000 PUT requests
        s3_storage_cost_per_gb = 0.023  # per GB per month
        dynamodb_write_cost = 1.25  # per million write units
        
        # Estimates
        s3_puts = num_files * 2  # upload + summary
        lambda_invocations = num_files
        lambda_gb_seconds = num_files * 0.5 * 5  # 512MB * avg 5 seconds
        dynamodb_writes = num_files
        
        s3_cost = (s3_puts / 1000) * s3_put_cost_per_1000
        lambda_request_cost = (lambda_invocations / 1_000_000) * lambda_cost_per_million
        lambda_duration_cost_total = lambda_gb_seconds * lambda_duration_cost
        dynamodb_cost = (dynamodb_writes / 1_000_000) * dynamodb_write_cost
        
        total_aws_cost = s3_cost + lambda_request_cost + lambda_duration_cost_total + dynamodb_cost
        
        print("💰 Estimated AWS Costs (per test run):")
        print(f"  • S3 requests:     ${s3_cost:.6f}")
        print(f"  • Lambda requests: ${lambda_request_cost:.6f}")
        print(f"  • Lambda duration: ${lambda_duration_cost_total:.6f}")
        print(f"  • DynamoDB writes: ${dynamodb_cost:.6f}")
        print(f"  • Total per run:   ${total_aws_cost:.6f}")
        
        print(f"\n💰 LocalStack Costs:")
        print(f"  • Per test run:    $0.00 (completely free)")
        print(f"  • Annual cost:     $0.00")
        
        # Extrapolate to real usage
        files_per_month = 10000
        monthly_runs = files_per_month / num_files if num_files > 0 else 0
        monthly_cost = total_aws_cost * monthly_runs
        annual_cost = monthly_cost * 12
        
        print(f"\n💰 Projected Costs (10,000 files/month):")
        print(f"  • AWS monthly:     ${monthly_cost:.2f}")
        print(f"  • AWS annual:      ${annual_cost:.2f}")
        print(f"  • LocalStack:      $0.00 (savings: ${annual_cost:.2f}/year)")
        
        print(f"\n📊 ROI Analysis:")
        print(f"  • Using LocalStack for dev/test saves real AWS costs")
        print(f"  • Break-even: Immediate (LocalStack Community is free)")
        print(f"  • Value: Risk-free experimentation + faster iteration")
    
    def generate_report(self):
        """Generate complete comparison report."""
        print("\n" + "="*80)
        print("  LOCALSTACK vs AWS - PERFORMANCE COMPARISON REPORT")
        print("="*80)
        
        print(f"\n📅 Test Date:")
        print(f"  • LocalStack: {self.localstack_data.get('timestamp', 'N/A')}")
        if self.aws_data:
            print(f"  • AWS:        {self.aws_data.get('timestamp', 'N/A')}")
        
        self.compare_latency()
        self.compare_throughput()
        self.compare_scalability()
        self.estimate_costs()
        self.generate_recommendations()
        
        print("\n" + "="*80)
        print("  END OF REPORT")
        print("="*80 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Compare LocalStack and AWS performance results')
    parser.add_argument('--localstack', required=True, help='LocalStack performance test results JSON file')
    parser.add_argument('--aws', help='AWS performance test results JSON file (optional)')
    args = parser.parse_args()
    
    comparison = EnvironmentComparison(args.localstack, args.aws)
    comparison.generate_report()

if __name__ == '__main__':
    main()

