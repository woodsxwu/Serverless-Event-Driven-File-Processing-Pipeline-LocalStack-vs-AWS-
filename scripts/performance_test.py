#!/usr/bin/env python3
"""
Comprehensive performance testing for LocalStack vs AWS comparison.
Tests throughput, latency, concurrency, and error handling.
"""

import argparse
import boto3
import json
import time
import sys
import csv
import io
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
import statistics

class PerformanceTest:
    def __init__(self, env: str):
        self.env = env
        self.results = {
            'environment': env,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tests': {}
        }
        self.s3_client, self.dynamodb = self._create_clients()
        self.bucket_name, self.table_name, self.lambda_name = self._get_terraform_outputs()
        
    def _create_clients(self):
        """Create AWS/LocalStack clients based on environment."""
        if self.env == 'localstack':
            endpoint_url = 'http://localhost:4566'
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
    
    def _get_terraform_outputs(self):
        """Get Terraform outputs."""
        try:
            result = subprocess.run(
                ['terraform', 'output', '-json'],
                cwd='../terraform',
                capture_output=True,
                text=True,
                check=True
            )
            outputs = json.loads(result.stdout)
            return (
                outputs['s3_bucket_name']['value'],
                outputs['dynamodb_table_name']['value'],
                outputs['lambda_function_name']['value']
            )
        except Exception as e:
            print(f"❌ Error getting Terraform outputs: {e}")
            sys.exit(1)
    
    def _create_csv_content(self, rows: int, file_id: int) -> str:
        """Create CSV content with specified number of rows."""
        lines = ["name,age,salary,join_date,department,city,country,employee_id"]
        
        cities = ["New York", "San Francisco", "London", "Tokyo", "Berlin", "Paris"]
        departments = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]
        
        for i in range(rows):
            name = f"Employee_{file_id}_{i}"
            age = 25 + (i % 40)
            salary = 50000 + (i * 1000) % 100000
            join_date = f"202{i % 5}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            department = departments[i % len(departments)]
            city = cities[i % len(cities)]
            country = "USA" if i % 3 == 0 else "UK"
            employee_id = f"EMP{file_id:04d}{i:04d}"
            
            lines.append(f"{name},{age},{salary},{join_date},{department},{city},{country},{employee_id}")
        
        return "\n".join(lines)
    
    def _upload_file(self, file_name: str, content: str) -> Tuple[bool, float, str]:
        """Upload a single file and return success, upload_time, error."""
        try:
            start_time = time.time()
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"uploads/{file_name}",
                Body=content.encode('utf-8'),
                ContentType='text/csv'
            )
            upload_time = time.time() - start_time
            return True, upload_time, None
        except Exception as e:
            return False, 0, str(e)
    
    def _wait_for_processing(self, file_name: str, timeout: int = 60) -> Tuple[bool, float, Dict]:
        """Wait for file to be processed and return success, processing_time, metadata."""
        table = self.dynamodb.Table(self.table_name)
        start_time = time.time()
        
        for attempt in range(timeout):
            try:
                response = table.get_item(Key={'file_name': file_name})
                if 'Item' in response:
                    processing_time = time.time() - start_time
                    return True, processing_time, dict(response['Item'])
                time.sleep(1)
            except Exception as e:
                if attempt == timeout - 1:
                    return False, time.time() - start_time, {'error': str(e)}
                time.sleep(1)
        
        return False, time.time() - start_time, {'error': 'Timeout'}
    
    def test_single_file_latency(self, num_runs: int = 10, rows_per_file: int = 100):
        """Test single file processing latency (sequential)."""
        print(f"\n📊 Test 1: Single File Latency ({num_runs} runs, {rows_per_file} rows each)")
        print("=" * 70)
        
        upload_times = []
        processing_times = []
        total_times = []
        failures = 0
        
        for i in range(num_runs):
            file_name = f"latency_test_{i}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.csv"
            content = self._create_csv_content(rows_per_file, i)
            
            # Upload
            start_time = time.time()
            success, upload_time, error = self._upload_file(file_name, content)
            
            if not success:
                print(f"   Run {i+1}: ❌ Upload failed - {error}")
                failures += 1
                continue
            
            upload_times.append(upload_time)
            
            # Wait for processing
            success, proc_time, metadata = self._wait_for_processing(file_name)
            total_time = time.time() - start_time
            
            if success:
                processing_times.append(proc_time)
                total_times.append(total_time)
                print(f"   Run {i+1}: ✅ Upload: {upload_time:.3f}s | Processing: {proc_time:.3f}s | Total: {total_time:.3f}s")
            else:
                failures += 1
                print(f"   Run {i+1}: ❌ Processing failed - {metadata.get('error', 'Unknown')}")
        
        self.results['tests']['single_file_latency'] = {
            'num_runs': num_runs,
            'rows_per_file': rows_per_file,
            'failures': failures,
            'upload_time': self._calculate_stats(upload_times),
            'processing_time': self._calculate_stats(processing_times),
            'total_time': self._calculate_stats(total_times)
        }
        
        print(f"\n📈 Results:")
        print(f"   Upload Time: {statistics.mean(upload_times):.3f}s avg (min: {min(upload_times):.3f}s, max: {max(upload_times):.3f}s)")
        print(f"   Processing Time: {statistics.mean(processing_times):.3f}s avg (min: {min(processing_times):.3f}s, max: {max(processing_times):.3f}s)")
        print(f"   Total Time: {statistics.mean(total_times):.3f}s avg (min: {min(total_times):.3f}s, max: {max(total_times):.3f}s)")
        print(f"   Success Rate: {((num_runs - failures) / num_runs * 100):.1f}%")
    
    def test_concurrent_processing(self, num_files: int = 20, rows_per_file: int = 50):
        """Test concurrent file uploads and processing."""
        print(f"\n📊 Test 2: Concurrent Processing ({num_files} files, {rows_per_file} rows each)")
        print("=" * 70)
        
        files_to_upload = []
        for i in range(num_files):
            file_name = f"concurrent_test_{i}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.csv"
            content = self._create_csv_content(rows_per_file, i)
            files_to_upload.append((file_name, content))
        
        # Upload all files concurrently
        upload_start = time.time()
        upload_results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._upload_file, fn, c): fn for fn, c in files_to_upload}
            
            for future in as_completed(futures):
                file_name = futures[future]
                success, upload_time, error = future.result()
                upload_results.append((file_name, success, upload_time, error))
        
        total_upload_time = time.time() - upload_start
        successful_uploads = [r for r in upload_results if r[1]]
        
        print(f"   ✅ Uploaded {len(successful_uploads)}/{num_files} files in {total_upload_time:.3f}s")
        print(f"   📈 Throughput: {len(successful_uploads) / total_upload_time:.2f} files/sec")
        
        # Wait for all processing concurrently
        processing_start = time.time()
        processing_results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._wait_for_processing, fn, 120): fn for fn, s, _, _ in upload_results if s}
            
            completed = 0
            for future in as_completed(futures):
                file_name = futures[future]
                success, proc_time, metadata = future.result()
                processing_results.append((file_name, success, proc_time, metadata))
                completed += 1
                if completed % 5 == 0:
                    print(f"   ⏳ Processed: {completed}/{len(successful_uploads)}")
        
        total_processing_time = time.time() - processing_start
        successful_processing = [r for r in processing_results if r[1]]
        
        print(f"   ✅ Processed {len(successful_processing)}/{len(successful_uploads)} files in {total_processing_time:.3f}s")
        print(f"   📈 Throughput: {len(successful_processing) / total_processing_time:.2f} files/sec")
        
        proc_times = [r[2] for r in processing_results if r[1]]
        
        self.results['tests']['concurrent_processing'] = {
            'num_files': num_files,
            'rows_per_file': rows_per_file,
            'successful_uploads': len(successful_uploads),
            'successful_processing': len(successful_processing),
            'total_upload_time': total_upload_time,
            'total_processing_time': total_processing_time,
            'upload_throughput': len(successful_uploads) / total_upload_time,
            'processing_throughput': len(successful_processing) / total_processing_time,
            'processing_times': self._calculate_stats(proc_times)
        }
    
    def test_large_file_handling(self, file_sizes: List[int] = [100, 500, 1000, 5000]):
        """Test handling of different file sizes."""
        print(f"\n📊 Test 3: Large File Handling")
        print("=" * 70)
        
        results = []
        
        for size in file_sizes:
            file_name = f"large_file_{size}_rows_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            content = self._create_csv_content(size, 999)
            
            print(f"   Testing {size} rows ({len(content) / 1024:.1f} KB)...")
            
            start_time = time.time()
            success, upload_time, error = self._upload_file(file_name, content)
            
            if not success:
                print(f"      ❌ Upload failed: {error}")
                results.append({'rows': size, 'success': False, 'error': error})
                continue
            
            success, proc_time, metadata = self._wait_for_processing(file_name, timeout=180)
            total_time = time.time() - start_time
            
            if success:
                rows_processed = int(metadata.get('row_count', 0))
                print(f"      ✅ Upload: {upload_time:.3f}s | Processing: {proc_time:.3f}s | Total: {total_time:.3f}s")
                print(f"         Throughput: {rows_processed / proc_time:.1f} rows/sec")
                results.append({
                    'rows': size,
                    'success': True,
                    'upload_time': upload_time,
                    'processing_time': proc_time,
                    'total_time': total_time,
                    'throughput': rows_processed / proc_time
                })
            else:
                print(f"      ❌ Processing failed: {metadata.get('error', 'Unknown')}")
                results.append({'rows': size, 'success': False, 'error': metadata.get('error')})
        
        self.results['tests']['large_file_handling'] = results
    
    def test_error_handling(self):
        """Test error handling with invalid files."""
        print(f"\n📊 Test 4: Error Handling")
        print("=" * 70)
        
        test_cases = [
            ('empty_file.csv', '', 'Empty file'),
            ('malformed.csv', 'not,valid,csv\ndata', 'Malformed CSV'),
            ('no_header.csv', '1,2,3\n4,5,6', 'No header row'),
        ]
        
        results = []
        
        for file_name, content, description in test_cases:
            file_name_full = f"{file_name.replace('.csv', '')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            print(f"   Testing: {description}")
            
            success, upload_time, error = self._upload_file(file_name_full, content)
            
            if not success:
                print(f"      ❌ Upload failed: {error}")
                results.append({'case': description, 'upload_success': False})
                continue
            
            success, proc_time, metadata = self._wait_for_processing(file_name_full, timeout=30)
            status = metadata.get('status', 'unknown')
            
            print(f"      Status: {status}")
            results.append({
                'case': description,
                'upload_success': True,
                'processing_status': status,
                'metadata': {k: str(v) for k, v in metadata.items() if k in ['status', 'error_message', 'row_count']}
            })
        
        self.results['tests']['error_handling'] = results
    
    def _calculate_stats(self, values: List[float]) -> Dict:
        """Calculate statistics from a list of values."""
        if not values:
            return {'count': 0}
        
        return {
            'count': len(values),
            'min': round(min(values), 3),
            'max': round(max(values), 3),
            'mean': round(statistics.mean(values), 3),
            'median': round(statistics.median(values), 3),
            'stdev': round(statistics.stdev(values), 3) if len(values) > 1 else 0
        }
    
    def save_results(self):
        """Save test results to JSON file."""
        filename = f"performance_{self.env}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to: {filename}")
        return filename
    
    def run_all_tests(self):
        """Run all performance tests."""
        print(f"\n{'='*70}")
        print(f"🚀 PERFORMANCE TEST SUITE - {self.env.upper()}")
        print(f"{'='*70}")
        print(f"📦 S3 Bucket: {self.bucket_name}")
        print(f"🗄️  DynamoDB Table: {self.table_name}")
        print(f"⚡ Lambda Function: {self.lambda_name}")
        
        start_time = time.time()
        
        try:
            self.test_single_file_latency(num_runs=10, rows_per_file=100)
            self.test_concurrent_processing(num_files=20, rows_per_file=50)
            self.test_large_file_handling(file_sizes=[100, 500, 1000, 2000])
            self.test_error_handling()
            
            total_time = time.time() - start_time
            self.results['total_test_time'] = round(total_time, 2)
            
            print(f"\n{'='*70}")
            print(f"✅ All tests completed in {total_time:.2f} seconds")
            print(f"{'='*70}")
            
            return self.save_results()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            return self.save_results()
        except Exception as e:
            print(f"\n\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    parser = argparse.ArgumentParser(description='Performance test suite for data ingestion pipeline')
    parser.add_argument('--env', choices=['localstack', 'aws'], required=True,
                        help='Environment to test (localstack or aws)')
    args = parser.parse_args()
    
    test_suite = PerformanceTest(args.env)
    test_suite.run_all_tests()

if __name__ == '__main__':
    main()

