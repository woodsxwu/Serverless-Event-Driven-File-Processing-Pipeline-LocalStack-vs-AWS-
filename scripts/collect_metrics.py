#!/usr/bin/env python3
"""
Collect CloudWatch metrics for Lambda and DynamoDB.
Useful for comparing LocalStack vs AWS performance.
"""

import argparse
import boto3
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List

def create_cloudwatch_client(env):
    """Create CloudWatch client based on environment."""
    if env == 'localstack':
        # Use dummy credentials for LocalStack
        return boto3.client('cloudwatch', 
                          endpoint_url='http://localhost:4566',
                          region_name='us-west-2',
                          aws_access_key_id='test',
                          aws_secret_access_key='test')
    else:
        return boto3.client('cloudwatch', region_name='us-west-2')

def get_terraform_outputs(env):
    """Get Terraform outputs for resource names."""
    import subprocess
    
    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            cwd='../terraform',
            capture_output=True,
            text=True,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        
        lambda_name = outputs['lambda_function_name']['value']
        table_name = outputs['dynamodb_table_name']['value']
        
        return lambda_name, table_name
    
    except Exception as e:
        print(f"Error getting Terraform outputs: {e}")
        sys.exit(1)

def get_metric_statistics(cloudwatch, namespace, metric_name, dimensions, 
                         start_time, end_time, period=60, statistic='Average'):
    """Get metric statistics from CloudWatch."""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )
        
        datapoints = response.get('Datapoints', [])
        if datapoints:
            # Sort by timestamp
            datapoints.sort(key=lambda x: x['Timestamp'])
            return datapoints
        return []
    
    except Exception as e:
        print(f"Error getting metric {metric_name}: {e}")
        return []

def collect_lambda_metrics(cloudwatch, lambda_name, start_time, end_time):
    """Collect Lambda metrics."""
    print(f"\n📊 Collecting Lambda Metrics for: {lambda_name}")
    print("-" * 70)
    
    dimensions = [{'Name': 'FunctionName', 'Value': lambda_name}]
    
    metrics = {
        'Duration': ('Milliseconds', 'Average'),
        'Invocations': ('Count', 'Sum'),
        'Errors': ('Count', 'Sum'),
        'Throttles': ('Count', 'Sum'),
        'ConcurrentExecutions': ('Count', 'Maximum'),
    }
    
    results = {}
    
    for metric_name, (unit, statistic) in metrics.items():
        print(f"\n  📈 {metric_name}:")
        datapoints = get_metric_statistics(
            cloudwatch,
            'AWS/Lambda',
            metric_name,
            dimensions,
            start_time,
            end_time,
            period=300,  # 5 minutes
            statistic=statistic
        )
        
        if datapoints:
            results[metric_name] = datapoints
            for dp in datapoints:
                timestamp = dp['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = dp.get(statistic, 0)
                print(f"     {timestamp}: {value:.2f} {unit}")
        else:
            print(f"     No data available")
            results[metric_name] = []
    
    return results

def collect_dynamodb_metrics(cloudwatch, table_name, start_time, end_time):
    """Collect DynamoDB metrics."""
    print(f"\n📊 Collecting DynamoDB Metrics for: {table_name}")
    print("-" * 70)
    
    dimensions = [{'Name': 'TableName', 'Value': table_name}]
    
    metrics = {
        'SuccessfulRequestLatency': ('Milliseconds', 'Average'),
        'ConsumedWriteCapacityUnits': ('Count', 'Sum'),
        'UserErrors': ('Count', 'Sum'),
        'SystemErrors': ('Count', 'Sum'),
    }
    
    results = {}
    
    for metric_name, (unit, statistic) in metrics.items():
        print(f"\n  📈 {metric_name}:")
        
        # Add operation dimension for latency metrics
        if metric_name == 'SuccessfulRequestLatency':
            dims = dimensions + [{'Name': 'Operation', 'Value': 'PutItem'}]
        else:
            dims = dimensions
        
        datapoints = get_metric_statistics(
            cloudwatch,
            'AWS/DynamoDB',
            metric_name,
            dims,
            start_time,
            end_time,
            period=300,  # 5 minutes
            statistic=statistic
        )
        
        if datapoints:
            results[metric_name] = datapoints
            for dp in datapoints:
                timestamp = dp['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = dp.get(statistic, 0)
                print(f"     {timestamp}: {value:.2f} {unit}")
        else:
            print(f"     No data available")
            results[metric_name] = []
    
    return results

def calculate_summary_statistics(metrics_data):
    """Calculate summary statistics from metrics."""
    summary = {}
    
    for metric_name, datapoints in metrics_data.items():
        if datapoints:
            values = []
            for dp in datapoints:
                # Get the statistic value (could be Average, Sum, Maximum, etc.)
                for key in ['Average', 'Sum', 'Maximum', 'Minimum']:
                    if key in dp:
                        values.append(dp[key])
                        break
            
            if values:
                summary[metric_name] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values),
                    'total': sum(values)
                }
    
    return summary

def print_summary(lambda_summary, dynamodb_summary):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("📊 SUMMARY STATISTICS")
    print("="*70)
    
    print("\n⚡ Lambda:")
    for metric, stats in lambda_summary.items():
        print(f"\n  {metric}:")
        print(f"    Min:     {stats['min']:.2f}")
        print(f"    Max:     {stats['max']:.2f}")
        print(f"    Average: {stats['avg']:.2f}")
        if metric in ['Invocations', 'Errors', 'Throttles']:
            print(f"    Total:   {stats['total']:.0f}")
    
    print("\n🗄️  DynamoDB:")
    for metric, stats in dynamodb_summary.items():
        print(f"\n  {metric}:")
        print(f"    Min:     {stats['min']:.2f}")
        print(f"    Max:     {stats['max']:.2f}")
        print(f"    Average: {stats['avg']:.2f}")
        if metric in ['ConsumedWriteCapacityUnits', 'UserErrors', 'SystemErrors']:
            print(f"    Total:   {stats['total']:.0f}")

def export_to_json(lambda_metrics, dynamodb_metrics, lambda_summary, dynamodb_summary, output_file):
    """Export metrics to JSON file."""
    data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'lambda_metrics': {
            'raw': lambda_metrics,
            'summary': lambda_summary
        },
        'dynamodb_metrics': {
            'raw': dynamodb_metrics,
            'summary': dynamodb_summary
        }
    }
    
    # Convert datetime objects to strings
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=convert_datetime)
    
    print(f"\n💾 Metrics exported to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Collect CloudWatch metrics')
    parser.add_argument('--env', choices=['localstack', 'aws'], required=True,
                       help='Environment to collect from (localstack or aws)')
    parser.add_argument('--hours', type=int, default=1,
                       help='Number of hours to look back (default: 1)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output JSON file (default: metrics_<env>_<timestamp>.json)')
    
    args = parser.parse_args()
    
    print(f"\n🚀 Collecting CloudWatch Metrics - {args.env.upper()}")
    print("="*70)
    
    # Get resource names
    lambda_name, table_name = get_terraform_outputs(args.env)
    
    # Create CloudWatch client
    cloudwatch = create_cloudwatch_client(args.env)
    
    # Set time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=args.hours)
    
    print(f"\n⏰ Time Range:")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Collect Lambda metrics
    lambda_metrics = collect_lambda_metrics(cloudwatch, lambda_name, start_time, end_time)
    
    # Collect DynamoDB metrics
    dynamodb_metrics = collect_dynamodb_metrics(cloudwatch, table_name, start_time, end_time)
    
    # Calculate summaries
    lambda_summary = calculate_summary_statistics(lambda_metrics)
    dynamodb_summary = calculate_summary_statistics(dynamodb_metrics)
    
    # Print summary
    if lambda_summary or dynamodb_summary:
        print_summary(lambda_summary, dynamodb_summary)
    else:
        print("\n⚠️  No metrics data available for the specified time range")
        print("   Make sure the pipeline has been executed recently!")
    
    # Export to JSON
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"metrics_{args.env}_{timestamp}.json"
    
    export_to_json(lambda_metrics, dynamodb_metrics, lambda_summary, 
                   dynamodb_summary, output_file)
    
    print("\n✅ Metrics collection completed!")

if __name__ == '__main__':
    main()

