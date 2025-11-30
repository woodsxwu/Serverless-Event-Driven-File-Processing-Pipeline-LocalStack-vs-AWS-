.PHONY: help localstack-up localstack-down deploy-localstack deploy-aws test-localstack test-aws perf-localstack perf-aws compare-performance metrics-localstack metrics-aws clean-localstack clean-aws experiments-localstack experiments-aws experiments-aws-safe compare-experiments

help:
	@echo "Data Ingestion Pipeline - Available Commands:"
	@echo ""
	@echo "  LocalStack:"
	@echo "    make localstack-up        - Start LocalStack container"
	@echo "    make localstack-down      - Stop LocalStack container"
	@echo "    make deploy-localstack    - Deploy to LocalStack"
	@echo "    make test-localstack      - Quick test LocalStack deployment"
	@echo "    make perf-localstack      - Run comprehensive performance tests"
	@echo "    make metrics-localstack   - Collect CloudWatch metrics (LocalStack)"
	@echo "    make experiments-localstack - Run all experiments (A-H)"
	@echo "    make clean-localstack     - Destroy LocalStack resources"
	@echo ""
	@echo "  AWS Learner Lab:"
	@echo "    make deploy-aws           - Deploy to AWS"
	@echo "    make test-aws             - Quick test AWS deployment"
	@echo "    make perf-aws             - Run comprehensive performance tests"
	@echo "    make metrics-aws          - Collect CloudWatch metrics (AWS)"
	@echo "    make experiments-aws-safe - Run safe experiments only (B,C,D,H)"
	@echo "    make experiments-aws      - Run all experiments (use with caution!)"
	@echo "    make clean-aws            - Destroy AWS resources"
	@echo ""
	@echo "  Comparison & Analysis:"
	@echo "    make compare-performance  - Compare performance test results"
	@echo "    make compare-experiments  - Compare experiment results (A-H)"
	@echo ""
	@echo "  Other:"
	@echo "    make install              - Install Python dependencies"
	@echo "    make lint                 - Check Terraform formatting"
	@echo ""

install:
	@echo "Installing Python dependencies..."
	pip3 install boto3
	@echo "✅ Dependencies installed!"

localstack-up:
	@echo "Starting LocalStack..."
	docker-compose up -d
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@echo "✅ LocalStack is running!"

localstack-down:
	@echo "Stopping LocalStack..."
	docker-compose down
	@echo "✅ LocalStack stopped!"

deploy-localstack: localstack-up
	@echo "Deploying to LocalStack..."
	@echo "Note: Using dummy credentials for LocalStack..."
	cd terraform && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		terraform init && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		terraform apply -var="environment=localstack" -auto-approve
	@echo "✅ Deployment complete!"

deploy-aws:
	@echo "Deploying to AWS Learner Lab..."
	@echo "Make sure your AWS credentials are configured!"
	@echo ""
	@echo "🔍 Auto-detecting AWS Learner Lab role..."
	@LAB_ROLE=$$(aws iam list-roles --query 'Roles[?RoleName==`LabRole`].Arn' --output text 2>/dev/null || echo ""); \
	if [ -n "$$LAB_ROLE" ]; then \
		echo "✅ Found LabRole: $$LAB_ROLE"; \
		echo "   Using existing Learner Lab role for Lambda execution."; \
		echo ""; \
		cd terraform && \
			terraform init && \
			terraform apply -var="environment=aws" -var="lab_role_arn=$$LAB_ROLE" -auto-approve; \
	else \
		echo "ℹ️  LabRole not found. Terraform will create a new Lambda execution role."; \
		echo "   (This is normal if you're not using AWS Learner Lab)"; \
		echo ""; \
		cd terraform && \
			terraform init && \
			terraform apply -var="environment=aws" -auto-approve; \
	fi
	@echo "✅ Deployment complete!"

test-localstack:
	@echo "Testing LocalStack deployment..."
	cd scripts && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		python3 test_pipeline.py --env localstack
	@echo "✅ Test complete!"

test-aws:
	@echo "Testing AWS deployment..."
	cd scripts && python3 test_pipeline.py --env aws
	@echo "✅ Test complete!"

perf-localstack:
	@echo "Running comprehensive performance tests on LocalStack..."
	@echo "This will take several minutes..."
	cd scripts && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		python3 performance_test.py --env localstack
	@echo "✅ Performance tests complete!"

perf-aws:
	@echo "Running comprehensive performance tests on AWS..."
	@echo "This will take several minutes..."
	cd scripts && python3 performance_test.py --env aws
	@echo "✅ Performance tests complete!"

compare-performance:
	@echo "Comparing performance results..."
	@cd scripts && \
		LOCALSTACK_FILE=$$(ls -t performance_localstack_*.json 2>/dev/null | head -1); \
		AWS_FILE=$$(ls -t performance_aws_*.json 2>/dev/null | head -1); \
		if [ -z "$$LOCALSTACK_FILE" ]; then \
			echo "❌ No LocalStack performance results found. Run 'make perf-localstack' first."; \
			exit 1; \
		fi; \
		if [ -z "$$AWS_FILE" ]; then \
			echo "⚠️  No AWS performance results found. Showing LocalStack results only."; \
			python3 compare_environments.py --localstack $$LOCALSTACK_FILE; \
		else \
			echo "📊 Comparing LocalStack ($$LOCALSTACK_FILE) vs AWS ($$AWS_FILE)"; \
			python3 compare_environments.py --localstack $$LOCALSTACK_FILE --aws $$AWS_FILE; \
		fi

metrics-localstack:
	@echo "Collecting CloudWatch metrics from LocalStack..."
	cd scripts && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		python3 collect_metrics.py --env localstack --hours 1
	@echo "✅ Metrics collected!"

metrics-aws:
	@echo "Collecting CloudWatch metrics..."
	cd scripts && python3 collect_metrics.py --env aws --hours 1
	@echo "✅ Metrics collected!"

clean-localstack:
	@echo "Destroying LocalStack resources..."
	cd terraform && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		terraform destroy -var="environment=localstack" -auto-approve
	@echo "✅ Resources destroyed!"

clean-aws:
	@echo "Destroying AWS resources..."
	@LAB_ROLE=$$(aws iam list-roles --query 'Roles[?RoleName==`LabRole`].Arn' --output text 2>/dev/null || echo ""); \
	cd terraform && \
		if [ -n "$$LAB_ROLE" ]; then \
			echo "Using LabRole: $$LAB_ROLE"; \
			terraform destroy -var="environment=aws" -var="lab_role_arn=$$LAB_ROLE" -auto-approve; \
		else \
			terraform destroy -var="environment=aws" -auto-approve; \
		fi
	@echo "✅ Resources destroyed!"

lint:
	@echo "Checking Terraform formatting..."
	cd terraform && terraform fmt -check
	@echo "✅ Terraform files are properly formatted!"

format:
	@echo "Formatting Terraform files..."
	cd terraform && terraform fmt -recursive
	@echo "✅ Terraform files formatted!"

# Experiment Suite Commands
experiments-localstack:
	@echo "🧪 Running comprehensive experiment suite on LocalStack..."
	@echo "This will run all experiments (A-H) and take 15-30 minutes..."
	@echo ""
	cd scripts && \
		unset AWS_PROFILE; \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_SESSION_TOKEN=test \
		AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
		python3 experiment_suite.py --env localstack
	@echo "✅ All experiments complete!"

experiments-aws-safe:
	@echo "🧪 Running lightweight experiment subset on AWS..."
	@echo "Running: B (E2E Timing), D (Failure Injection), H (IAM)"
	@echo "This will take ~5 minutes and uses minimal resources..."
	@echo ""
	cd scripts && python3 experiment_suite.py --env aws --experiments B D H
	@echo "✅ Lightweight experiments complete!"

experiments-aws:
	@echo "🧪 Running FULL experiment suite on AWS..."
	@echo ""
	@echo "⚠️  This will run all experiments at the SAME SCALE as LocalStack:"
	@echo "   • 100 concurrent file uploads"
	@echo "   • Files up to 20,000 rows"
	@echo "   • Up to 100 parallel uploads"
	@echo ""
	@echo "   Estimated: 30-45 minutes, ~500 Lambda invocations, $$2-5 cost"
	@echo ""
	@read -p "Continue with full test suite? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		cd scripts && python3 experiment_suite.py --env aws; \
		echo "✅ All experiments complete!"; \
	else \
		echo "❌ Cancelled. Use 'make experiments-aws-safe' for lightweight testing."; \
	fi

compare-experiments:
	@echo "📊 Comparing experiment results..."
	@cd scripts && \
		LOCALSTACK_FILE=$$(ls -t experiments_localstack_*.json 2>/dev/null | head -1); \
		AWS_FILE=$$(ls -t experiments_aws_*.json 2>/dev/null | head -1); \
		if [ -z "$$LOCALSTACK_FILE" ]; then \
			echo "❌ No LocalStack experiment results found."; \
			echo "   Run 'make experiments-localstack' first."; \
			exit 1; \
		fi; \
		if [ -z "$$AWS_FILE" ]; then \
			echo "❌ No AWS experiment results found."; \
			echo "   Run 'make experiments-aws-safe' first."; \
			exit 1; \
		fi; \
		echo ""; \
		echo "📁 LocalStack: $$LOCALSTACK_FILE"; \
		echo "📁 AWS:        $$AWS_FILE"; \
		echo ""; \
		python3 compare_experiments.py --localstack $$LOCALSTACK_FILE --aws $$AWS_FILE; \
		echo ""; \
		echo "💾 To save report: python3 compare_experiments.py --localstack $$LOCALSTACK_FILE --aws $$AWS_FILE --output report.txt"

