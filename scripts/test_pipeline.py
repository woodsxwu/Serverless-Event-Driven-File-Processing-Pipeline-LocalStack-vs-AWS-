#!/usr/bin/env python3
"""
Test script for the data ingestion pipeline.
Uploads a CSV file, polls DynamoDB for completion, and verifies results.
"""

import argparse
import boto3
import json
import time
import sys
from datetime import datetime
import csv
import io

def create_test_csv():
    """Create a sample CSV file for testing."""
    csv_content = """name,age,salary,join_date
Alice,30,75000.50,2022-01-15
Bob,25,65000.00,2022-03-20
Charlie,35,85000.75,2021-11-10
Diana,28,70000.00,2022-05-01
Eve,32,80000.25,2021-09-15
Frank,29,,2022-02-10
Grace,31,77000.50,invalid_date
Henry,invalid,72000.00,2022-04-05
"""
    return csv_content

def create_clients(env):
    """Create AWS/LocalStack clients based on environment."""
    if env == 'localstack':
        endpoint_url = 'http://localhost:4566'
        # Use dummy credentials for LocalStack
        # Note: LocalStack uses us-west-2 to match Terraform configuration
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            region_name='us-west-2',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=endpoint_url,
            region_name='us-west-2',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
    else:
        s3 = boto3.client('s3', region_name='us-west-2')
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    
    return s3, dynamodb

def get_terraform_outputs(env):
    """Get Terraform outputs for bucket and table names."""
    import subprocess
    
    try:
        # Change to terraform directory
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            cwd='../terraform',
            capture_output=True,
            text=True,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        
        bucket_name = outputs['s3_bucket_name']['value']
        table_name = outputs['dynamodb_table_name']['value']
        lambda_name = outputs['lambda_function_name']['value']
        
        return bucket_name, table_name, lambda_name
    
    except Exception as e:
        print(f"Error getting Terraform outputs: {e}")
        print("Make sure Terraform has been applied first!")
        sys.exit(1)

def upload_file(s3_client, bucket_name, file_name, content):
    """Upload CSV file to S3."""
    key = f"uploads/{file_name}"
    print(f"\n📤 Uploading {file_name} to s3://{bucket_name}/{key}")
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/csv'
        )
        print(f"✅ Upload successful!")
        return key
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)

def poll_dynamodb(dynamodb, table_name, file_name, max_attempts=30, delay=2):
    """Poll DynamoDB for processing completion."""
    print(f"\n⏳ Polling DynamoDB table '{table_name}' for {file_name}...")
    
    table = dynamodb.Table(table_name)
    
    for attempt in range(max_attempts):
        try:
            response = table.get_item(Key={'file_name': file_name})
            
            if 'Item' in response:
                item = response['Item']
                print(f"✅ Record found after {attempt + 1} attempts!")
                return item
            
            time.sleep(delay)
            print(f"   Attempt {attempt + 1}/{max_attempts}...", end='\r')
        
        except Exception as e:
            print(f"\n❌ Error querying DynamoDB: {e}")
            time.sleep(delay)
    
    print(f"\n❌ Timeout: File not processed after {max_attempts * delay} seconds")
    return None

def verify_summary_json(s3_client, bucket_name, file_name):
    """Verify that summary JSON was created."""
    summary_key = f"processed/{file_name.replace('.csv', '')}_summary.json"
    print(f"\n🔍 Checking for summary JSON at s3://{bucket_name}/{summary_key}")
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=summary_key)
        summary = json.loads(response['Body'].read().decode('utf-8'))
        print(f"✅ Summary JSON found!")
        return summary
    except Exception as e:
        print(f"❌ Summary JSON not found: {e}")
        return None

def print_results(metadata, summary):
    """Pretty print the processing results."""
    print("\n" + "="*70)
    print("📊 PROCESSING RESULTS")
    print("="*70)
    
    # Basic info
    print(f"\n📁 File: {metadata['file_name']}")
    print(f"📅 Upload Time: {metadata['upload_timestamp']}")
    print(f"⚙️  Processed Time: {metadata['processed_timestamp']}")
    print(f"✅ Status: {metadata['status']}")
    
    if metadata['status'] == 'error':
        print(f"❌ Error: {metadata.get('error_message', 'Unknown error')}")
        return
    
    # Row count
    print(f"📏 Row Count: {metadata['row_count']}")
    
    # Schema
    print(f"\n🔤 Schema:")
    schema = dict(metadata['schema'])
    for col, dtype in schema.items():
        print(f"   - {col}: {dtype}")
    
    # Statistics
    print(f"\n📈 Statistics:")
    stats = dict(metadata['statistics'])
    if stats:
        for col, col_stats in stats.items():
            print(f"   - {col}:")
            for stat_name, stat_value in col_stats.items():
                if stat_name != 'count':
                    print(f"      {stat_name}: {float(stat_value):.2f}")
    else:
        print("   (No numeric columns)")
    
    # Quality issues
    print(f"\n⚠️  Quality Issues:")
    quality = dict(metadata['quality_issues'])
    
    if not quality.get('has_issues', False):
        print("   ✅ No issues detected!")
    else:
        missing = quality.get('missing_values', {})
        if missing:
            print(f"   Missing values:")
            for col, info in missing.items():
                print(f"      - {col}: {info['count']} ({float(info['percentage']):.1f}%)")
        
        invalid = quality.get('invalid_values', {})
        if invalid:
            print(f"   Invalid values:")
            for col, info in invalid.items():
                print(f"      - {col}: {info['count']} ({float(info['percentage']):.1f}%) - expected {info['expected_type']}")
    
    print("\n" + "="*70)

def main():
    parser = argparse.ArgumentParser(description='Test the data ingestion pipeline')
    parser.add_argument('--env', choices=['localstack', 'aws'], required=True,
                       help='Environment to test (localstack or aws)')
    parser.add_argument('--file', type=str, default=None,
                       help='Path to CSV file to upload (default: generate test CSV)')
    
    args = parser.parse_args()
    
    print(f"\n🚀 Testing Data Ingestion Pipeline - {args.env.upper()}")
    print("="*70)
    
    # Get Terraform outputs
    bucket_name, table_name, lambda_name = get_terraform_outputs(args.env)
    print(f"\n📦 S3 Bucket: {bucket_name}")
    print(f"🗄️  DynamoDB Table: {table_name}")
    print(f"⚡ Lambda Function: {lambda_name}")
    
    # Create clients
    s3_client, dynamodb = create_clients(args.env)
    
    # Prepare test file
    if args.file:
        with open(args.file, 'r') as f:
            csv_content = f.read()
        file_name = args.file.split('/')[-1]
    else:
        csv_content = create_test_csv()
        file_name = f"test_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Upload file
    upload_start = time.time()
    upload_file(s3_client, bucket_name, file_name, csv_content)
    
    # Poll for completion
    metadata = poll_dynamodb(dynamodb, table_name, file_name)
    
    if not metadata:
        print("\n❌ Test failed: Processing did not complete")
        sys.exit(1)
    
    # Calculate processing time
    processing_time = time.time() - upload_start
    print(f"\n⏱️  Total processing time: {processing_time:.2f} seconds")
    
    # Verify summary JSON
    summary = verify_summary_json(s3_client, bucket_name, file_name)
    
    # Print results
    print_results(metadata, summary)
    
    print(f"\n✅ Test completed successfully!")

if __name__ == '__main__':
    main()

