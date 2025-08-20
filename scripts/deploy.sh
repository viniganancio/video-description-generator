#!/bin/bash

# Video Description Generator Deployment Script
# Usage: ./scripts/deploy.sh [environment] [action]
# Example: ./scripts/deploy.sh dev deploy

set -e

# Default values
ENVIRONMENT=${1:-dev}
ACTION=${2:-deploy}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate requirements
validate_requirements() {
    log_info "Validating requirements..."
    
    # Check required tools
    local required_tools=("terraform" "aws" "python3" "pip3" "zip")
    for tool in "${required_tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    if [[ ! "$python_version" =~ ^3\.(9|10|11) ]]; then
        log_warning "Python version $python_version detected. Python 3.9+ recommended."
    fi
    
    log_success "All requirements validated"
}

# Build Lambda layers
build_lambda_layers() {
    log_info "Building Lambda layers..."
    
    local layers_dir="$PROJECT_ROOT/src/layers"
    mkdir -p "$layers_dir"
    
    # Create dependencies layer
    log_info "Creating dependencies layer..."
    local temp_deps_dir=$(mktemp -d)
    
    # Install dependencies for Lambda layer
    pip3 install --target "$temp_deps_dir/python" \
        yt-dlp \
        requests \
        boto3 \
        botocore
    
    # Create layer zip
    cd "$temp_deps_dir"
    zip -r "$layers_dir/dependencies.zip" python/
    cd "$PROJECT_ROOT"
    
    # Clean up
    rm -rf "$temp_deps_dir"
    
    log_success "Lambda layers built successfully"
}

# Package Lambda functions
package_lambda_functions() {
    log_info "Packaging Lambda functions..."
    
    # Package processor function
    log_info "Packaging video processor function..."
    cd "$PROJECT_ROOT/src/processors"
    if [ -f "package.zip" ]; then
        rm package.zip
    fi
    zip -r package.zip . -x "__pycache__/*" "*.pyc" "tests/*"
    cd "$PROJECT_ROOT"
    
    # Package API handler function
    log_info "Packaging API handler function..."
    cd "$PROJECT_ROOT/src/handlers"
    if [ -f "package.zip" ]; then
        rm package.zip
    fi
    zip -r package.zip . -x "__pycache__/*" "*.pyc" "tests/*"
    cd "$PROJECT_ROOT"
    
    log_success "Lambda functions packaged successfully"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure for environment: $ENVIRONMENT"
    
    cd "$PROJECT_ROOT/terraform"
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Select or create workspace
    terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"
    
    # Plan deployment
    log_info "Planning Terraform deployment..."
    terraform plan -var-file="environments/${ENVIRONMENT}.tfvars" -out="tfplan"
    
    # Apply deployment
    log_info "Applying Terraform deployment..."
    terraform apply "tfplan"
    
    # Save outputs
    log_info "Saving Terraform outputs..."
    terraform output -json > "../deployment-outputs-${ENVIRONMENT}.json"
    
    cd "$PROJECT_ROOT"
    
    log_success "Infrastructure deployed successfully"
}

# Update Lambda function code
update_lambda_code() {
    log_info "Updating Lambda function code..."
    
    # Get function names from Terraform outputs
    if [ ! -f "deployment-outputs-${ENVIRONMENT}.json" ]; then
        log_error "Deployment outputs not found. Please deploy infrastructure first."
        exit 1
    fi
    
    local processor_function=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.lambda_processor_function_name.value')
    local api_function=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.lambda_api_function_name.value')
    
    # Update processor function
    log_info "Updating processor function: $processor_function"
    aws lambda update-function-code \
        --function-name "$processor_function" \
        --zip-file "fileb://src/processors/package.zip" \
        --region "$AWS_REGION"
    
    # Update API function
    log_info "Updating API function: $api_function"
    aws lambda update-function-code \
        --function-name "$api_function" \
        --zip-file "fileb://src/handlers/package.zip" \
        --region "$AWS_REGION"
    
    log_success "Lambda function code updated successfully"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Check if tests exist
    if [ -d "$PROJECT_ROOT/tests" ]; then
        cd "$PROJECT_ROOT"
        python3 -m pytest tests/ -v
    else
        log_warning "No tests directory found, skipping tests"
    fi
    
    log_success "Tests completed"
}

# Smoke test deployment
smoke_test() {
    log_info "Running smoke tests..."
    
    if [ ! -f "deployment-outputs-${ENVIRONMENT}.json" ]; then
        log_warning "No deployment outputs found, skipping smoke tests"
        return
    fi
    
    local api_url=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.api_gateway_url.value')
    
    if [ "$api_url" != "null" ] && [ -n "$api_url" ]; then
        log_info "Testing API Gateway endpoint: $api_url"
        
        # Test with a simple YouTube URL
        local test_response=$(curl -s -w "%{http_code}" -o /tmp/smoke_test_response \
            -X POST "$api_url/analyze" \
            -H "Content-Type: application/json" \
            -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' || echo "000")
        
        if [ "$test_response" = "202" ]; then
            log_success "API endpoint is responding correctly"
            local job_id=$(cat /tmp/smoke_test_response | jq -r '.job_id')
            log_info "Test job created: $job_id"
        else
            log_warning "API endpoint test returned HTTP $test_response"
        fi
        
        rm -f /tmp/smoke_test_response
    else
        log_warning "API Gateway URL not found in outputs"
    fi
}

# Destroy infrastructure
destroy_infrastructure() {
    log_warning "Destroying infrastructure for environment: $ENVIRONMENT"
    read -p "Are you sure? This action cannot be undone. Type 'yes' to confirm: " -r
    
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Destruction cancelled"
        return
    fi
    
    cd "$PROJECT_ROOT/terraform"
    
    terraform workspace select "$ENVIRONMENT"
    terraform plan -destroy -var-file="environments/${ENVIRONMENT}.tfvars" -out="destroy-plan"
    terraform apply "destroy-plan"
    
    cd "$PROJECT_ROOT"
    
    log_success "Infrastructure destroyed"
}

# Show deployment info
show_info() {
    log_info "Deployment Information for environment: $ENVIRONMENT"
    
    if [ -f "deployment-outputs-${ENVIRONMENT}.json" ]; then
        echo "=== Terraform Outputs ==="
        cat "deployment-outputs-${ENVIRONMENT}.json" | jq '.'
        echo ""
        
        # Extract key information
        local api_url=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.api_gateway_url.value')
        local s3_bucket=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.s3_bucket_name.value')
        local dynamodb_table=$(cat "deployment-outputs-${ENVIRONMENT}.json" | jq -r '.dynamodb_table_name.value')
        
        echo "=== Quick Access URLs ==="
        echo "API Gateway: $api_url"
        echo "S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/$s3_bucket"
        echo "DynamoDB Table: https://console.aws.amazon.com/dynamodbv2/home?region=$AWS_REGION#table?name=$dynamodb_table"
        echo "CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups"
    else
        log_warning "No deployment outputs found for environment: $ENVIRONMENT"
    fi
}

# Main deployment function
main() {
    log_info "Starting deployment process..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Action: $ACTION"
    log_info "AWS Region: $AWS_REGION"
    
    case $ACTION in
        "deploy")
            validate_requirements
            build_lambda_layers
            package_lambda_functions
            deploy_infrastructure
            smoke_test
            show_info
            ;;
        "update-code")
            validate_requirements
            package_lambda_functions
            update_lambda_code
            ;;
        "test")
            run_tests
            ;;
        "smoke-test")
            smoke_test
            ;;
        "destroy")
            destroy_infrastructure
            ;;
        "info")
            show_info
            ;;
        *)
            log_error "Unknown action: $ACTION"
            echo "Available actions: deploy, update-code, test, smoke-test, destroy, info"
            exit 1
            ;;
    esac
    
    log_success "Deployment process completed successfully!"
}

# Execute main function
main "$@"