#!/bin/bash

# API Testing Script for Video Description Generator
# Usage: ./scripts/test-api.sh [api_base_url] [test_type]

set -e

API_BASE_URL=${1:-""}
TEST_TYPE=${2:-"basic"}

# Color codes
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

# Get API URL from Terraform outputs if not provided
get_api_url() {
    if [ -z "$API_BASE_URL" ]; then
        if [ -f "deployment-outputs-dev.json" ]; then
            API_BASE_URL=$(cat deployment-outputs-dev.json | jq -r '.api_gateway_url.value')
            log_info "Using API URL from deployment outputs: $API_BASE_URL"
        else
            log_error "No API URL provided and no deployment outputs found"
            log_info "Usage: $0 <api_base_url> [test_type]"
            exit 1
        fi
    fi
}

# Test CORS preflight request
test_cors() {
    log_info "Testing CORS preflight request..."
    
    local response=$(curl -s -w "%{http_code}" -o /tmp/cors_response \
        -X OPTIONS "$API_BASE_URL/analyze" \
        -H "Origin: https://example.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type")
    
    if [ "$response" = "200" ]; then
        log_success "CORS preflight request successful"
        
        # Check CORS headers
        if curl -s -I -X OPTIONS "$API_BASE_URL/analyze" | grep -q "Access-Control-Allow-Origin"; then
            log_success "CORS headers present"
        else
            log_warning "CORS headers missing"
        fi
    else
        log_error "CORS preflight request failed with HTTP $response"
    fi
    
    rm -f /tmp/cors_response
}

# Test analyze endpoint with YouTube URL
test_analyze_youtube() {
    log_info "Testing analyze endpoint with YouTube URL..."
    
    local test_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    local response=$(curl -s -w "%{http_code}" -o /tmp/analyze_response \
        -X POST "$API_BASE_URL/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"video_url\": \"$test_url\"}")
    
    if [ "$response" = "202" ]; then
        log_success "Analyze request accepted"
        
        local job_id=$(cat /tmp/analyze_response | jq -r '.job_id')
        if [ "$job_id" != "null" ] && [ -n "$job_id" ]; then
            log_success "Job ID received: $job_id"
            echo "JOB_ID=$job_id" > /tmp/test_job_id
        else
            log_error "No job ID in response"
        fi
    else
        log_error "Analyze request failed with HTTP $response"
        cat /tmp/analyze_response
    fi
    
    rm -f /tmp/analyze_response
}

# Test analyze endpoint with direct video URL
test_analyze_direct() {
    log_info "Testing analyze endpoint with direct video URL..."
    
    local test_url="https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    local response=$(curl -s -w "%{http_code}" -o /tmp/analyze_direct_response \
        -X POST "$API_BASE_URL/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"video_url\": \"$test_url\"}")
    
    if [ "$response" = "202" ]; then
        log_success "Direct video analyze request accepted"
        
        local job_id=$(cat /tmp/analyze_direct_response | jq -r '.job_id')
        if [ "$job_id" != "null" ] && [ -n "$job_id" ]; then
            log_success "Job ID received: $job_id"
        fi
    else
        log_warning "Direct video analyze request failed with HTTP $response (may be expected if URL is not accessible)"
        cat /tmp/analyze_direct_response
    fi
    
    rm -f /tmp/analyze_direct_response
}

# Test status endpoint
test_status() {
    if [ ! -f "/tmp/test_job_id" ]; then
        log_warning "No job ID available for status test"
        return
    fi
    
    local job_id=$(cat /tmp/test_job_id | cut -d'=' -f2)
    log_info "Testing status endpoint for job: $job_id"
    
    local response=$(curl -s -w "%{http_code}" -o /tmp/status_response \
        -X GET "$API_BASE_URL/status/$job_id")
    
    if [ "$response" = "200" ]; then
        log_success "Status request successful"
        
        local status=$(cat /tmp/status_response | jq -r '.status')
        log_info "Job status: $status"
        
        # Pretty print the response
        echo "Status Response:"
        cat /tmp/status_response | jq '.'
    else
        log_error "Status request failed with HTTP $response"
        cat /tmp/status_response
    fi
    
    rm -f /tmp/status_response
}

# Test result endpoint
test_result() {
    if [ ! -f "/tmp/test_job_id" ]; then
        log_warning "No job ID available for result test"
        return
    fi
    
    local job_id=$(cat /tmp/test_job_id | cut -d'=' -f2)
    log_info "Testing result endpoint for job: $job_id"
    
    # Test basic result
    local response=$(curl -s -w "%{http_code}" -o /tmp/result_response \
        -X GET "$API_BASE_URL/result/$job_id")
    
    log_info "Result request returned HTTP $response"
    
    if [ -f "/tmp/result_response" ]; then
        echo "Result Response:"
        cat /tmp/result_response | jq '.'
        
        # If completed, test with detailed analysis
        local status=$(cat /tmp/result_response | jq -r '.status // empty')
        if [ "$status" = "completed" ]; then
            log_info "Job completed, testing detailed result..."
            
            curl -s -X GET "$API_BASE_URL/result/$job_id?include_analysis=true" | jq '.'
        fi
    fi
    
    rm -f /tmp/result_response
}

# Test error conditions
test_error_conditions() {
    log_info "Testing error conditions..."
    
    # Test missing video_url
    log_info "Testing missing video_url..."
    local response=$(curl -s -w "%{http_code}" -o /tmp/error_response \
        -X POST "$API_BASE_URL/analyze" \
        -H "Content-Type: application/json" \
        -d '{}')
    
    if [ "$response" = "400" ]; then
        log_success "Missing video_url handled correctly (HTTP 400)"
    else
        log_warning "Missing video_url returned HTTP $response (expected 400)"
    fi
    
    # Test invalid video URL
    log_info "Testing invalid video URL..."
    response=$(curl -s -w "%{http_code}" -o /tmp/error_response \
        -X POST "$API_BASE_URL/analyze" \
        -H "Content-Type: application/json" \
        -d '{"video_url": "not-a-valid-url"}')
    
    if [ "$response" = "400" ]; then
        log_success "Invalid video URL handled correctly (HTTP 400)"
    else
        log_warning "Invalid video URL returned HTTP $response (expected 400)"
    fi
    
    # Test non-existent job ID
    log_info "Testing non-existent job ID..."
    response=$(curl -s -w "%{http_code}" -o /tmp/error_response \
        -X GET "$API_BASE_URL/status/non-existent-job-id")
    
    if [ "$response" = "404" ]; then
        log_success "Non-existent job ID handled correctly (HTTP 404)"
    else
        log_warning "Non-existent job ID returned HTTP $response (expected 404)"
    fi
    
    rm -f /tmp/error_response
}

# Test API health/endpoints
test_endpoints() {
    log_info "Testing API endpoints availability..."
    
    # Test invalid endpoint
    local response=$(curl -s -w "%{http_code}" -o /tmp/endpoint_response \
        -X GET "$API_BASE_URL/invalid-endpoint")
    
    if [ "$response" = "404" ]; then
        log_success "Invalid endpoint handled correctly (HTTP 404)"
    else
        log_warning "Invalid endpoint returned HTTP $response (expected 404)"
    fi
    
    rm -f /tmp/endpoint_response
}

# Monitor job progress (optional)
monitor_job() {
    if [ ! -f "/tmp/test_job_id" ]; then
        log_warning "No job ID available for monitoring"
        return
    fi
    
    local job_id=$(cat /tmp/test_job_id | cut -d'=' -f2)
    log_info "Monitoring job progress: $job_id"
    
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local response=$(curl -s "$API_BASE_URL/status/$job_id")
        local status=$(echo "$response" | jq -r '.status // "unknown"')
        
        log_info "Attempt $attempt/$max_attempts - Status: $status"
        
        if [ "$status" = "completed" ]; then
            log_success "Job completed successfully!"
            echo "Final result:"
            curl -s "$API_BASE_URL/result/$job_id" | jq '.'
            break
        elif [ "$status" = "failed" ]; then
            log_error "Job failed"
            echo "Error details:"
            echo "$response" | jq '.'
            break
        elif [ "$status" = "processing" ] || [ "$status" = "pending" ]; then
            log_info "Job still $status, waiting..."
            sleep 30
        else
            log_warning "Unknown status: $status"
            sleep 10
        fi
        
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_warning "Job monitoring timeout after $max_attempts attempts"
    fi
}

# Performance test
performance_test() {
    log_info "Running basic performance test..."
    
    local start_time=$(date +%s)
    
    # Send multiple requests
    for i in {1..5}; do
        log_info "Sending request $i/5..."
        curl -s -o /dev/null -w "Request $i: %{time_total}s\n" \
            -X POST "$API_BASE_URL/analyze" \
            -H "Content-Type: application/json" \
            -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
        sleep 1
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Performance test completed in ${duration} seconds"
}

# Main test function
main() {
    log_info "Starting API tests for Video Description Generator"
    log_info "Test type: $TEST_TYPE"
    
    get_api_url
    
    case $TEST_TYPE in
        "basic")
            test_cors
            test_analyze_youtube
            test_status
            test_result
            test_error_conditions
            test_endpoints
            ;;
        "analyze")
            test_analyze_youtube
            test_analyze_direct
            ;;
        "monitor")
            test_analyze_youtube
            monitor_job
            ;;
        "errors")
            test_error_conditions
            ;;
        "performance")
            performance_test
            ;;
        "full")
            test_cors
            test_analyze_youtube
            test_analyze_direct
            test_status
            test_result
            test_error_conditions
            test_endpoints
            performance_test
            ;;
        *)
            log_error "Unknown test type: $TEST_TYPE"
            log_info "Available test types: basic, analyze, monitor, errors, performance, full"
            exit 1
            ;;
    esac
    
    # Cleanup
    rm -f /tmp/test_job_id
    
    log_success "API tests completed!"
}

# Execute main function
main "$@"