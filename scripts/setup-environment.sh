#!/bin/bash

# Environment Setup Script for Video Description Generator
# Sets up development environment and installs dependencies

set -e

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check if running on macOS or Linux
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Install Homebrew on macOS
install_homebrew() {
    if ! command -v brew &> /dev/null; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        log_info "Homebrew already installed"
    fi
}

# Install required system dependencies
install_system_dependencies() {
    local os=$(detect_os)
    
    log_info "Installing system dependencies for $os..."
    
    if [ "$os" = "macos" ]; then
        install_homebrew
        
        # Install required packages
        brew install \
            python@3.11 \
            terraform \
            awscli \
            jq \
            ffmpeg \
            wget \
            curl
            
    elif [ "$os" = "linux" ]; then
        # Update package list
        sudo apt-get update
        
        # Install required packages
        sudo apt-get install -y \
            python3.11 \
            python3.11-venv \
            python3-pip \
            wget \
            curl \
            unzip \
            jq \
            ffmpeg
        
        # Install Terraform
        if ! command -v terraform &> /dev/null; then
            log_info "Installing Terraform..."
            wget -O- https://apt.releases.hashicorp.com/gpg | \
                gpg --dearmor | \
                sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
                https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
                sudo tee /etc/apt/sources.list.d/hashicorp.list
            sudo apt update
            sudo apt-get install terraform
        fi
        
        # Install AWS CLI
        if ! command -v aws &> /dev/null; then
            log_info "Installing AWS CLI..."
            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
            unzip awscliv2.zip
            sudo ./aws/install
            rm -rf aws awscliv2.zip
        fi
        
    else
        log_error "Unsupported operating system: $os"
        log_info "Please install the following manually:"
        log_info "- Python 3.11+"
        log_info "- Terraform"
        log_info "- AWS CLI"
        log_info "- jq"
        log_info "- ffmpeg"
        exit 1
    fi
}

# Create and setup Python virtual environment
setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3.11 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    pip install -r requirements-dev.txt
    
    log_success "Python environment setup complete"
}

# Configure AWS CLI (interactive)
configure_aws() {
    log_info "Configuring AWS CLI..."
    
    if aws sts get-caller-identity &> /dev/null; then
        log_info "AWS CLI already configured and working"
        aws sts get-caller-identity
    else
        log_warning "AWS CLI not configured or credentials invalid"
        echo "Please configure AWS CLI with your credentials:"
        aws configure
        
        # Test configuration
        if aws sts get-caller-identity &> /dev/null; then
            log_success "AWS CLI configuration successful"
        else
            log_error "AWS CLI configuration failed"
            exit 1
        fi
    fi
}

# Initialize Terraform backend (optional)
init_terraform_backend() {
    log_info "Initializing Terraform backend..."
    
    cd "$PROJECT_ROOT/terraform"
    
    # Create backend configuration if it doesn't exist
    if [ ! -f "backend.tf" ]; then
        log_warning "No backend.tf found. Using local backend."
        cat > backend.tf << EOF
terraform {
  backend "local" {}
}
EOF
    fi
    
    terraform init
    
    cd "$PROJECT_ROOT"
    
    log_success "Terraform backend initialized"
}

# Validate environment setup
validate_setup() {
    log_info "Validating environment setup..."
    
    local errors=0
    
    # Check Python
    if command -v python3.11 &> /dev/null; then
        log_success "Python 3.11 installed"
    else
        log_error "Python 3.11 not found"
        ((errors++))
    fi
    
    # Check Terraform
    if command -v terraform &> /dev/null; then
        local tf_version=$(terraform version | head -1)
        log_success "Terraform installed: $tf_version"
    else
        log_error "Terraform not found"
        ((errors++))
    fi
    
    # Check AWS CLI
    if command -v aws &> /dev/null; then
        local aws_version=$(aws --version)
        log_success "AWS CLI installed: $aws_version"
    else
        log_error "AWS CLI not found"
        ((errors++))
    fi
    
    # Check jq
    if command -v jq &> /dev/null; then
        log_success "jq installed"
    else
        log_error "jq not found"
        ((errors++))
    fi
    
    # Check ffmpeg
    if command -v ffmpeg &> /dev/null; then
        log_success "ffmpeg installed"
    else
        log_warning "ffmpeg not found (optional for video processing)"
    fi
    
    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        log_success "AWS credentials configured"
    else
        log_error "AWS credentials not configured"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        log_success "Environment validation passed!"
    else
        log_error "Environment validation failed with $errors errors"
        exit 1
    fi
}

# Create sample configuration files
create_sample_configs() {
    log_info "Creating sample configuration files..."
    
    # Create local environment file
    if [ ! -f "$PROJECT_ROOT/.env.local" ]; then
        cat > "$PROJECT_ROOT/.env.local" << EOF
# Local Development Environment Variables
AWS_REGION=us-east-1
MAX_VIDEO_SIZE_MB=100
VIDEO_PROCESSING_TIMEOUT=600
LOG_LEVEL=DEBUG
ENABLE_DEBUG_LOGGING=true
ENABLE_CACHING=false

# Override these with your actual values
# S3_BUCKET_NAME=your-video-bucket-dev
# DYNAMODB_TABLE_NAME=your-video-jobs-dev
# BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
EOF
        log_info "Created .env.local with sample values"
    fi
    
    # Create pre-commit configuration
    if [ ! -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]; then
        cat > "$PROJECT_ROOT/.pre-commit-config.yaml" << EOF
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
EOF
        log_info "Created .pre-commit-config.yaml"
    fi
}

# Main setup function
main() {
    log_info "Starting environment setup for Video Description Generator"
    log_info "Project root: $PROJECT_ROOT"
    
    install_system_dependencies
    setup_python_environment
    configure_aws
    init_terraform_backend
    create_sample_configs
    validate_setup
    
    log_success "Environment setup completed successfully!"
    
    echo ""
    log_info "Next steps:"
    log_info "1. Review and update .env.local with your configuration"
    log_info "2. Update terraform/environments/dev.tfvars as needed"
    log_info "3. Run './scripts/deploy.sh dev deploy' to deploy the infrastructure"
    echo ""
    log_info "To activate the Python virtual environment:"
    log_info "source venv/bin/activate"
}

# Execute main function
main "$@"