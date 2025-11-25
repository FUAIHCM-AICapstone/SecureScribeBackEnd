#!/bin/bash

# SecureScribe Backend Test Runner
# This script provides convenient commands for running tests locally and in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Commands
run_all_tests() {
    print_header "Running All Tests"
    pytest tests/ -v
}

run_tests_with_coverage() {
    print_header "Running Tests with Coverage"
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
    print_success "Coverage report generated in htmlcov/index.html"
}

run_specific_test() {
    if [ -z "$1" ]; then
        print_error "Please provide test file or pattern"
        echo "Usage: $0 test <file_or_pattern>"
        exit 1
    fi
    print_header "Running Tests: $1"
    pytest tests/ -k "$1" -v
}

run_docker_tests() {
    print_header "Running Tests in Docker"
    docker-compose -f docker-compose.local.yml --profile test up test
}

run_docker_tests_background() {
    print_header "Running Tests in Docker (Background)"
    docker-compose -f docker-compose.local.yml --profile test up -d test
    print_info "Tests running in background. View logs with: docker-compose -f docker-compose.local.yml logs -f test"
}

view_docker_logs() {
    print_header "Viewing Docker Test Logs"
    docker-compose -f docker-compose.local.yml logs -f test
}

stop_docker_tests() {
    print_header "Stopping Docker Tests"
    docker-compose -f docker-compose.local.yml --profile test down
    print_success "Docker test service stopped"
}

view_coverage_report() {
    print_header "Opening Coverage Report"
    if [ -f "htmlcov/index.html" ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        elif command -v open &> /dev/null; then
            open htmlcov/index.html
        elif command -v start &> /dev/null; then
            start htmlcov/index.html
        else
            print_error "Cannot open browser. Please open htmlcov/index.html manually"
        fi
    else
        print_error "Coverage report not found. Run tests with coverage first: $0 coverage"
    fi
}

view_docker_coverage_report() {
    print_header "Opening Docker Coverage Report"
    if [ -f "coverage_reports/html/index.html" ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open coverage_reports/html/index.html
        elif command -v open &> /dev/null; then
            open coverage_reports/html/index.html
        elif command -v start &> /dev/null; then
            start coverage_reports/html/index.html
        else
            print_error "Cannot open browser. Please open coverage_reports/html/index.html manually"
        fi
    else
        print_error "Coverage report not found. Run Docker tests first: $0 docker"
    fi
}

run_linting() {
    print_header "Running Linting"
    if command -v ruff &> /dev/null; then
        ruff check tests/ app/
    else
        print_error "ruff not installed. Install with: pip install ruff"
    fi
}

show_help() {
    cat << EOF
${BLUE}SecureScribe Backend Test Runner${NC}

Usage: $0 <command> [options]

Commands:
  all              Run all tests
  coverage         Run tests with coverage report
  test <pattern>   Run specific tests matching pattern
  docker           Run tests in Docker
  docker-bg        Run tests in Docker (background)
  logs             View Docker test logs
  stop             Stop Docker tests
  report           Open coverage report (local)
  report-docker    Open coverage report (Docker)
  lint             Run linting checks
  help             Show this help message

Examples:
  $0 all                    # Run all tests
  $0 coverage               # Run tests with coverage
  $0 test user              # Run tests matching 'user'
  $0 docker                 # Run tests in Docker
  $0 report                 # Open coverage report

EOF
}

# Main
case "${1:-help}" in
    all)
        run_all_tests
        ;;
    coverage)
        run_tests_with_coverage
        ;;
    test)
        run_specific_test "$2"
        ;;
    docker)
        run_docker_tests
        ;;
    docker-bg)
        run_docker_tests_background
        ;;
    logs)
        view_docker_logs
        ;;
    stop)
        stop_docker_tests
        ;;
    report)
        view_coverage_report
        ;;
    report-docker)
        view_docker_coverage_report
        ;;
    lint)
        run_linting
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
