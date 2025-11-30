#!/usr/bin/env python3
"""
Compare experiment results from LocalStack vs AWS

Generates comprehensive comparison reports showing the differences
between LocalStack and AWS across all experiments.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any, List
import os

class ExperimentComparator:
    """Compare and analyze experiment results"""
    
    def __init__(self, localstack_file: str, aws_file: str):
        self.localstack_results = self._load_results(localstack_file)
        self.aws_results = self._load_results(aws_file)
        
        if not self.localstack_results or not self.aws_results:
            print("❌ Failed to load results files")
            sys.exit(1)
        
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT COMPARISON: LocalStack vs AWS")
        print(f"{'='*70}")
        print(f"LocalStack: {localstack_file}")
        print(f"AWS:        {aws_file}")
        print(f"{'='*70}\n")
    
    def _load_results(self, filename: str) -> Dict:
        """Load experiment results from JSON file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return None
    
    def _format_stats(self, stats: Dict) -> str:
        """Format statistics dictionary for display"""
        if not stats or stats.get('count', 0) == 0:
            return "No data"
        
        return (f"mean={stats.get('mean', 0):.3f}s, "
                f"p95={stats.get('p95', 0):.3f}s, "
                f"min={stats.get('min', 0):.3f}s, "
                f"max={stats.get('max', 0):.3f}s")
    
    def _calculate_speedup(self, localstack_val: float, aws_val: float) -> str:
        """Calculate speedup factor"""
        if aws_val == 0 or localstack_val == 0:
            return "N/A"
        
        speedup = aws_val / localstack_val
        if speedup > 1:
            return f"{speedup:.1f}× faster"
        else:
            return f"{1/speedup:.1f}× slower"
    
    def compare_experiment_a(self):
        """Compare Experiment A: Deployment Speed"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT A: Deployment Speed")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('A_deployment_speed', {})
        aws_exp = self.aws_results['experiments'].get('A_deployment_speed', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        ls_times = ls_exp.get('times', {})
        aws_times = aws_exp.get('times', {})
        
        print(f"Operation:")
        print(f"  LocalStack: {ls_exp.get('operation', 'unknown')}")
        print(f"  AWS:        {aws_exp.get('operation', 'unknown')}")
        
        print(f"\n{'Metric':<20} {'LocalStack':<30} {'AWS':<30} {'Comparison':<20}")
        print(f"{'-'*100}")
        
        ls_mean = ls_times.get('mean', 0)
        aws_mean = aws_times.get('mean', 0)
        
        print(f"{'Mean Time':<20} {ls_mean:.2f}s{'':<25} {aws_mean:.2f}s{'':<25} {self._calculate_speedup(ls_mean, aws_mean):<20}")
        print(f"{'P95 Time':<20} {ls_times.get('p95', 0):.2f}s{'':<25} {aws_times.get('p95', 0):.2f}s{'':<25}")
        print(f"{'Min Time':<20} {ls_times.get('min', 0):.2f}s{'':<25} {aws_times.get('min', 0):.2f}s{'':<25}")
        print(f"{'Max Time':<20} {ls_times.get('max', 0):.2f}s{'':<25} {aws_times.get('max', 0):.2f}s{'':<25}")
        
        print(f"\n💡 Insights:")
        if ls_mean < aws_mean:
            speedup = aws_mean / ls_mean
            print(f"   • LocalStack deployment is {speedup:.1f}× faster than AWS")
            print(f"   • This demonstrates LocalStack's advantage for CI/CD pipelines")
        else:
            print(f"   • AWS deployment is faster (unexpected - may indicate plan vs apply)")
    
    def compare_experiment_b(self):
        """Compare Experiment B: End-to-End Pipeline Timing"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT B: End-to-End Pipeline Timing")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('B_e2e_timing', {})
        aws_exp = self.aws_results['experiments'].get('B_e2e_timing', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        print(f"Test Parameters:")
        print(f"  Runs:     {ls_exp.get('num_runs', 0)} (LocalStack), {aws_exp.get('num_runs', 0)} (AWS)")
        print(f"  Rows:     {ls_exp.get('rows_per_file', 0)} per file")
        print(f"  Failures: {ls_exp.get('failures', 0)} (LocalStack), {aws_exp.get('failures', 0)} (AWS)")
        
        metrics = [
            ('T_upload', 'Upload Time'),
            ('T_event_latency', 'Event Latency'),
            ('T_processing', 'Processing Time'),
            ('T_total_pipeline', 'Total Pipeline Time')
        ]
        
        print(f"\n{'Metric':<25} {'LocalStack (mean/p95)':<30} {'AWS (mean/p95)':<30} {'Speedup':<20}")
        print(f"{'-'*105}")
        
        for metric_key, metric_name in metrics:
            ls_stats = ls_exp.get(metric_key, {})
            aws_stats = aws_exp.get(metric_key, {})
            
            ls_mean = ls_stats.get('mean', 0)
            ls_p95 = ls_stats.get('p95', 0)
            aws_mean = aws_stats.get('mean', 0)
            aws_p95 = aws_stats.get('p95', 0)
            
            ls_str = f"{ls_mean:.3f}s / {ls_p95:.3f}s"
            aws_str = f"{aws_mean:.3f}s / {aws_p95:.3f}s"
            speedup = self._calculate_speedup(ls_mean, aws_mean)
            
            print(f"{metric_name:<25} {ls_str:<30} {aws_str:<30} {speedup:<20}")
        
        print(f"\n💡 Insights:")
        ls_total = ls_exp.get('T_total_pipeline', {}).get('mean', 0)
        aws_total = aws_exp.get('T_total_pipeline', {}).get('mean', 0)
        
        if ls_total < aws_total:
            speedup = aws_total / ls_total
            print(f"   • LocalStack pipeline is {speedup:.1f}× faster end-to-end")
            print(f"   • This is expected due to local network and stub services")
        
        ls_event = ls_exp.get('T_event_latency', {}).get('mean', 0)
        aws_event = aws_exp.get('T_event_latency', {}).get('mean', 0)
        
        if aws_event > ls_event * 2:
            print(f"   • AWS shows significantly higher event latency ({aws_event:.3f}s vs {ls_event:.3f}s)")
            print(f"   • This reflects real-world S3 event notification delays")
    
    
    def compare_experiment_d(self):
        """Compare Experiment D: Failure Injection"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT D: Failure Injection")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('D_failure_injection', {})
        aws_exp = self.aws_results['experiments'].get('D_failure_injection', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        ls_cases = ls_exp.get('test_cases', [])
        aws_cases = aws_exp.get('test_cases', [])
        
        print(f"{'Test Case':<25} {'LocalStack Status':<20} {'AWS Status':<20} {'Match':<10}")
        print(f"{'-'*75}")
        
        # Match test cases by name
        for ls_case in ls_cases:
            test_name = ls_case.get('test', 'Unknown')
            aws_case = next((c for c in aws_cases if c.get('test') == test_name), None)
            
            ls_status = ls_case.get('actual_status', 'unknown')
            aws_status = aws_case.get('actual_status', 'unknown') if aws_case else 'N/A'
            
            match = "✅" if ls_status == aws_status else "❌"
            
            print(f"{test_name:<25} {ls_status:<20} {aws_status:<20} {match:<10}")
        
        ls_matches = ls_exp.get('matches', 0)
        aws_matches = aws_exp.get('matches', 0)
        ls_total = ls_exp.get('total_tests', 0)
        aws_total = aws_exp.get('total_tests', 0)
        
        print(f"\nSummary:")
        print(f"  LocalStack: {ls_matches}/{ls_total} tests behaved as expected")
        print(f"  AWS:        {aws_matches}/{aws_total} tests behaved as expected")
        
        print(f"\n💡 Insights:")
        
        # Check for divergences
        divergences = []
        for ls_case in ls_cases:
            test_name = ls_case.get('test', 'Unknown')
            aws_case = next((c for c in aws_cases if c.get('test') == test_name), None)
            
            if aws_case:
                ls_status = ls_case.get('actual_status', 'unknown')
                aws_status = aws_case.get('actual_status', 'unknown')
                
                if ls_status != aws_status:
                    divergences.append((test_name, ls_status, aws_status))
        
        if divergences:
            print(f"   ⚠️  Found {len(divergences)} divergence(s) in error handling:")
            for test, ls_s, aws_s in divergences:
                print(f"      • {test}: LocalStack={ls_s}, AWS={aws_s}")
        else:
            print(f"   ✅ LocalStack and AWS handle errors consistently")
    
    
    def compare_experiment_f(self):
        """Compare Experiment F: File Size Scaling"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT F: File Size Scaling")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('F_file_size_scaling', {})
        aws_exp = self.aws_results['experiments'].get('F_file_size_scaling', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        ls_results = ls_exp.get('results', [])
        aws_results = aws_exp.get('results', [])
        
        print(f"{'Rows':<10} {'File Size':<12} {'LocalStack Time':<20} {'AWS Time':<20} {'Speedup':<15}")
        print(f"{'-'*77}")
        
        # Match results by row count
        all_sizes = sorted(set([r['rows'] for r in ls_results] + [r['rows'] for r in aws_results]))
        
        for size in all_sizes:
            ls_result = next((r for r in ls_results if r['rows'] == size), None)
            aws_result = next((r for r in aws_results if r['rows'] == size), None)
            
            if ls_result and aws_result and ls_result.get('success') and aws_result.get('success'):
                file_size = f"{ls_result['file_size_kb']:.1f} KB"
                ls_time = ls_result['processing_time']
                aws_time = aws_result['processing_time']
                speedup = self._calculate_speedup(ls_time, aws_time)
                
                print(f"{size:<10} {file_size:<12} {ls_time:.3f}s{'':<14} {aws_time:.3f}s{'':<14} {speedup:<15}")
            elif ls_result and aws_result:
                file_size = f"{ls_result.get('file_size_kb', aws_result.get('file_size_kb', 0)):.1f} KB"
                ls_status = "✅" if ls_result.get('success') else "❌"
                aws_status = "✅" if aws_result.get('success') else "❌"
                print(f"{size:<10} {file_size:<12} {ls_status:<20} {aws_status:<20} {'N/A':<15}")
        
        print(f"\n💡 Insights:")
        
        # Check for scaling patterns
        ls_successful = [r for r in ls_results if r.get('success')]
        aws_successful = [r for r in aws_results if r.get('success')]
        
        if len(ls_successful) >= 2:
            ls_throughputs = [r.get('throughput_rows_per_sec', 0) for r in ls_successful]
            ls_avg_throughput = sum(ls_throughputs) / len(ls_throughputs)
            print(f"   • LocalStack avg throughput: {ls_avg_throughput:.1f} rows/sec")
        
        if len(aws_successful) >= 2:
            aws_throughputs = [r.get('throughput_rows_per_sec', 0) for r in aws_successful]
            aws_avg_throughput = sum(aws_throughputs) / len(aws_throughputs)
            print(f"   • AWS avg throughput: {aws_avg_throughput:.1f} rows/sec")
        
        # Check for non-linear scaling
        if len(ls_successful) >= 3:
            first_time = ls_successful[0]['processing_time']
            last_time = ls_successful[-1]['processing_time']
            first_rows = ls_successful[0]['rows']
            last_rows = ls_successful[-1]['rows']
            
            expected_time = first_time * (last_rows / first_rows)
            actual_time = last_time
            
            if actual_time > expected_time * 1.5:
                print(f"   ⚠️  Non-linear scaling detected (expected {expected_time:.1f}s, got {actual_time:.1f}s)")
    
    def compare_experiment_g(self):
        """Compare Experiment G: Parallel Scaling"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT G: Parallel Upload Scaling")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('G_parallel_scaling', {})
        aws_exp = self.aws_results['experiments'].get('G_parallel_scaling', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        ls_results = ls_exp.get('results', [])
        aws_results = aws_exp.get('results', [])
        
        print(f"{'N Files':<10} {'Environment':<15} {'Upload T/put':<15} {'Process T/put':<15} {'Success Rate':<15}")
        print(f"{'-'*70}")
        
        # Get all parallel levels
        all_levels = sorted(set([r['parallel_level'] for r in ls_results] + [r['parallel_level'] for r in aws_results]))
        
        for level in all_levels:
            ls_result = next((r for r in ls_results if r['parallel_level'] == level), None)
            aws_result = next((r for r in aws_results if r['parallel_level'] == level), None)
            
            if ls_result:
                upload_tput = ls_result['upload_throughput']
                process_tput = ls_result['processing_throughput']
                success_rate = (ls_result['successful_processing'] / ls_result['parallel_level']) * 100
                
                print(f"{level:<10} {'LocalStack':<15} {upload_tput:.2f} f/s{'':<6} {process_tput:.2f} f/s{'':<6} {success_rate:.1f}%{'':<8}")
            
            if aws_result:
                upload_tput = aws_result['upload_throughput']
                process_tput = aws_result['processing_throughput']
                success_rate = (aws_result['successful_processing'] / aws_result['parallel_level']) * 100
                
                print(f"{level:<10} {'AWS':<15} {upload_tput:.2f} f/s{'':<6} {process_tput:.2f} f/s{'':<6} {success_rate:.1f}%{'':<8}")
            
            if ls_result and aws_result:
                print()  # Blank line between levels
        
        print(f"\n💡 Insights:")
        
        # Check for scaling efficiency
        if len(ls_results) >= 2:
            ls_first = ls_results[0]
            ls_last = ls_results[-1]
            
            scaling_factor = ls_last['parallel_level'] / ls_first['parallel_level']
            throughput_factor = ls_last['processing_throughput'] / ls_first['processing_throughput']
            efficiency = (throughput_factor / scaling_factor) * 100
            
            print(f"   • LocalStack scaling efficiency: {efficiency:.1f}%")
            if efficiency < 50:
                print(f"     (throughput does not scale linearly with parallelism)")
        
        if len(aws_results) >= 2:
            aws_first = aws_results[0]
            aws_last = aws_results[-1]
            
            scaling_factor = aws_last['parallel_level'] / aws_first['parallel_level']
            throughput_factor = aws_last['processing_throughput'] / aws_first['processing_throughput']
            efficiency = (throughput_factor / scaling_factor) * 100
            
            print(f"   • AWS scaling efficiency: {efficiency:.1f}%")
    
    def compare_experiment_h(self):
        """Compare Experiment H: IAM Fidelity"""
        print(f"\n{'='*70}")
        print(f"📊 EXPERIMENT H: IAM Policy Fidelity")
        print(f"{'='*70}\n")
        
        ls_exp = self.localstack_results['experiments'].get('H_iam_fidelity', {})
        aws_exp = self.aws_results['experiments'].get('H_iam_fidelity', {})
        
        if not ls_exp or not aws_exp:
            print("⚠️  Incomplete data for this experiment\n")
            return
        
        ls_tests = ls_exp.get('tests', [])
        aws_tests = aws_exp.get('tests', [])
        
        print(f"{'Test':<35} {'LocalStack':<15} {'AWS':<15} {'Match':<10}")
        print(f"{'-'*75}")
        
        for ls_test in ls_tests:
            test_name = ls_test.get('test', 'Unknown')
            aws_test = next((t for t in aws_tests if t.get('test') == test_name), None)
            
            ls_actual = ls_test.get('actual', 'unknown')
            aws_actual = aws_test.get('actual', 'unknown') if aws_test else 'N/A'
            
            match = "✅" if ls_actual == aws_actual else "❌"
            
            print(f"{test_name:<35} {ls_actual:<15} {aws_actual:<15} {match:<10}")
        
        print(f"\nSummary:")
        print(f"  LocalStack: {ls_exp.get('matches', 0)}/{ls_exp.get('total_tests', 0)} tests passed")
        print(f"  AWS:        {aws_exp.get('matches', 0)}/{aws_exp.get('total_tests', 0)} tests passed")
        
        print(f"\n💡 Insights:")
        
        # Check for IAM divergences
        divergences = []
        for ls_test in ls_tests:
            test_name = ls_test.get('test', 'Unknown')
            aws_test = next((t for t in aws_tests if t.get('test') == test_name), None)
            
            if aws_test:
                ls_actual = ls_test.get('actual', 'unknown')
                aws_actual = aws_test.get('actual', 'unknown')
                
                if ls_actual != aws_actual:
                    divergences.append((test_name, ls_actual, aws_actual))
        
        if divergences:
            print(f"   ⚠️  Found {len(divergences)} IAM behavior divergence(s):")
            for test, ls_a, aws_a in divergences:
                print(f"      • {test}: LocalStack={ls_a}, AWS={aws_a}")
            print(f"   → LocalStack's IAM enforcement is less strict than AWS")
            print(f"   → Always validate IAM policies in real AWS before production")
        else:
            print(f"   ✅ IAM behavior is consistent between LocalStack and AWS")
            print(f"   → Basic permission validation can be done in LocalStack")
    
    def generate_summary(self):
        """Generate overall summary and recommendations"""
        print(f"\n{'='*70}")
        print(f"📋 OVERALL SUMMARY & RECOMMENDATIONS")
        print(f"{'='*70}\n")
        
        print("🎯 When to Use LocalStack:")
        print("   ✅ Rapid development and inner-loop testing")
        print("   ✅ CI/CD pipelines (faster feedback)")
        print("   ✅ Unit and integration testing")
        print("   ✅ Cost-free experimentation")
        print("   ✅ Offline development")
        
        print("\n🎯 When to Use AWS Learner Lab / Real AWS:")
        print("   ✅ Final integration testing before production")
        print("   ✅ Performance benchmarking and capacity planning")
        print("   ✅ IAM and security policy validation")
        print("   ✅ Testing real-world latency and error conditions")
        print("   ✅ Validating event trigger reliability")
        
        print("\n⚠️  Key Differences Found:")
        
        # Check for major divergences
        b_exp_ls = self.localstack_results['experiments'].get('B_e2e_timing', {})
        b_exp_aws = self.aws_results['experiments'].get('B_e2e_timing', {})
        
        if b_exp_ls and b_exp_aws:
            ls_time = b_exp_ls.get('T_total_pipeline', {}).get('mean', 0)
            aws_time = b_exp_aws.get('T_total_pipeline', {}).get('mean', 0)
            
            if ls_time > 0 and aws_time > 0:
                speedup = aws_time / ls_time
                print(f"   • Performance: LocalStack is ~{speedup:.1f}× faster for E2E pipeline")
        
        print("\n💡 Best Practice Workflow:")
        print("   1. Develop & test locally with LocalStack")
        print("   2. Run comprehensive test suite in LocalStack CI")
        print("   3. Run focused correctness tests in AWS staging")
        print("   4. Validate IAM, performance, and scaling in AWS")
        print("   5. Deploy to AWS production with confidence")
        
        print(f"\n{'='*70}\n")
    
    def generate_report(self):
        """Generate complete comparison report"""
        experiments = [
            ('A', self.compare_experiment_a),
            ('B', self.compare_experiment_b),
            ('D', self.compare_experiment_d),
            ('F', self.compare_experiment_f),
            ('G', self.compare_experiment_g),
            ('H', self.compare_experiment_h)
        ]
        
        for exp_id, compare_func in experiments:
            try:
                compare_func()
            except Exception as e:
                print(f"\n❌ Error comparing experiment {exp_id}: {e}")
        
        self.generate_summary()


def main():
    parser = argparse.ArgumentParser(
        description='Compare LocalStack vs AWS experiment results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python3 compare_experiments.py \\
    --localstack experiments_localstack_20251130_120000.json \\
    --aws experiments_aws_20251130_120000.json
        """
    )
    
    parser.add_argument('--localstack', required=True,
                        help='Path to LocalStack experiment results JSON')
    parser.add_argument('--aws', required=True,
                        help='Path to AWS experiment results JSON')
    parser.add_argument('--output', default=None,
                        help='Optional: Save report to file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.localstack):
        print(f"❌ LocalStack results file not found: {args.localstack}")
        sys.exit(1)
    
    if not os.path.exists(args.aws):
        print(f"❌ AWS results file not found: {args.aws}")
        sys.exit(1)
    
    comparator = ExperimentComparator(args.localstack, args.aws)
    
    if args.output:
        # Redirect stdout to file
        original_stdout = sys.stdout
        with open(args.output, 'w') as f:
            sys.stdout = f
            comparator.generate_report()
        sys.stdout = original_stdout
        print(f"\n💾 Report saved to: {args.output}")
    else:
        comparator.generate_report()


if __name__ == '__main__':
    main()

