"""
Lambda function to process CSV files from S3.
Infers schema, computes statistics, detects quality issues,
and writes metadata to DynamoDB.
"""

import json
import csv
import io
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
import boto3
from decimal import Decimal

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
TABLE_NAME = os.environ['DYNAMODB_TABLE']
BUCKET_NAME = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    """
    Main Lambda handler for S3 event notifications.
    """
    try:
        # Extract S3 event details
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        upload_timestamp = record['eventTime']
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Only process files in uploads/ prefix
        if not key.startswith('uploads/'):
            print(f"Skipping file not in uploads/ prefix: {key}")
            return {'statusCode': 200, 'body': 'Skipped'}
        
        # Get file name
        file_name = key.split('/')[-1]
        
        # Process the CSV file
        try:
            result = process_csv_file(bucket, key, file_name, upload_timestamp)
            status = "success"
            error_message = None
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            result = {
                'file_name': file_name,
                'row_count': 0,
                'schema': {},
                'statistics': {},
                'quality_issues': {'error': str(e)}
            }
            status = "error"
            error_message = str(e)
        
        # Write metadata to DynamoDB
        write_metadata_to_dynamodb(
            file_name=file_name,
            schema=result['schema'],
            statistics=result['statistics'],
            quality_issues=result['quality_issues'],
            upload_timestamp=upload_timestamp,
            status=status,
            error_message=error_message,
            row_count=result['row_count']
        )
        
        print(f"Successfully processed {file_name}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File processed successfully',
                'file_name': file_name,
                'status': status
            })
        }
        
    except Exception as e:
        print(f"Fatal error in lambda_handler: {str(e)}")
        raise


def process_csv_file(bucket: str, key: str, file_name: str, upload_timestamp: str) -> Dict[str, Any]:
    """
    Download and process CSV file from S3.
    Returns schema, statistics, and quality issues.
    """
    # Download file from S3
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(content))
    rows = list(csv_reader)
    
    if not rows:
        raise ValueError("CSV file is empty or has no data rows")
    
    # Get column names
    columns = list(rows[0].keys())
    
    # Infer schema and collect data
    schema = infer_schema(rows, columns)
    
    # Compute statistics
    statistics = compute_statistics(rows, schema)
    
    # Detect quality issues
    quality_issues = detect_quality_issues(rows, schema)
    
    # Generate summary JSON
    summary = {
        'file_name': file_name,
        'upload_timestamp': upload_timestamp,
        'processed_timestamp': datetime.utcnow().isoformat() + 'Z',
        'row_count': len(rows),
        'column_count': len(columns),
        'schema': schema,
        'statistics': statistics,
        'quality_issues': quality_issues
    }
    
    # Upload summary to processed/ prefix
    summary_key = f"processed/{file_name.replace('.csv', '')}_summary.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=summary_key,
        Body=json.dumps(summary, indent=2),
        ContentType='application/json'
    )
    
    print(f"Uploaded summary to s3://{bucket}/{summary_key}")
    
    return {
        'file_name': file_name,
        'row_count': len(rows),
        'schema': schema,
        'statistics': statistics,
        'quality_issues': quality_issues
    }


def infer_schema(rows: List[Dict], columns: List[str]) -> Dict[str, str]:
    """
    Infer data types for each column.
    Types: int, float, date, string
    """
    schema = {}
    
    for col in columns:
        # Collect non-empty values
        values = [row[col] for row in rows if row[col].strip()]
        
        if not values:
            schema[col] = 'string'
            continue
        
        # Try to infer type
        col_type = infer_column_type(values)
        schema[col] = col_type
    
    return schema


def infer_column_type(values: List[str]) -> str:
    """
    Infer the type of a column based on its values.
    """
    # Try integer
    try:
        for val in values:
            int(val)
        return 'int'
    except ValueError:
        pass
    
    # Try float
    try:
        for val in values:
            float(val)
        return 'float'
    except ValueError:
        pass
    
    # Try date (simple check for common formats)
    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
    for fmt in date_formats:
        try:
            for val in values[:10]:  # Check first 10 values
                datetime.strptime(val, fmt)
            return 'date'
        except ValueError:
            continue
    
    return 'string'


def compute_statistics(rows: List[Dict], schema: Dict[str, str]) -> Dict[str, Any]:
    """
    Compute statistics for numeric columns.
    """
    statistics = {}
    
    for col, col_type in schema.items():
        if col_type in ['int', 'float']:
            # Get numeric values
            values = []
            for row in rows:
                try:
                    if col_type == 'int':
                        values.append(int(row[col]))
                    else:
                        values.append(float(row[col]))
                except (ValueError, KeyError):
                    pass
            
            if values:
                statistics[col] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values)
                }
    
    return statistics


def detect_quality_issues(rows: List[Dict], schema: Dict[str, str]) -> Dict[str, Any]:
    """
    Detect data quality issues:
    - Missing values
    - Invalid values (type mismatches)
    """
    total_rows = len(rows)
    issues = {
        'total_rows': total_rows,
        'missing_values': {},
        'invalid_values': {},
        'has_issues': False
    }
    
    for col, col_type in schema.items():
        # Count missing values
        missing = sum(1 for row in rows if not row.get(col, '').strip())
        if missing > 0:
            issues['missing_values'][col] = {
                'count': missing,
                'percentage': round(missing / total_rows * 100, 2)
            }
            issues['has_issues'] = True
        
        # Count invalid values for typed columns
        if col_type in ['int', 'float']:
            invalid = 0
            for row in rows:
                val = row.get(col, '').strip()
                if val:  # Only check non-empty values
                    try:
                        if col_type == 'int':
                            int(val)
                        else:
                            float(val)
                    except ValueError:
                        invalid += 1
            
            if invalid > 0:
                issues['invalid_values'][col] = {
                    'count': invalid,
                    'percentage': round(invalid / total_rows * 100, 2),
                    'expected_type': col_type
                }
                issues['has_issues'] = True
    
    return issues


def write_metadata_to_dynamodb(
    file_name: str,
    schema: Dict[str, str],
    statistics: Dict[str, Any],
    quality_issues: Dict[str, Any],
    upload_timestamp: str,
    status: str,
    error_message: str = None,
    row_count: int = 0
):
    """
    Write processing metadata to DynamoDB table.
    """
    table = dynamodb.Table(TABLE_NAME)
    
    # Convert floats to Decimal for DynamoDB
    statistics_decimal = json.loads(
        json.dumps(statistics), 
        parse_float=Decimal
    )
    quality_issues_decimal = json.loads(
        json.dumps(quality_issues), 
        parse_float=Decimal
    )
    
    item = {
        'file_name': file_name,
        'upload_timestamp': upload_timestamp,
        'processed_timestamp': datetime.utcnow().isoformat() + 'Z',
        'status': status,
        'row_count': row_count,
        'schema': schema,
        'statistics': statistics_decimal,
        'quality_issues': quality_issues_decimal
    }
    
    if error_message:
        item['error_message'] = error_message
    
    table.put_item(Item=item)
    print(f"Written metadata to DynamoDB for {file_name}")

