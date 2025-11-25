@echo off
REM SecureScribe Backend Test Runner for Windows
REM This script provides convenient commands for running tests locally and in Docker

setlocal enabledelayedexpansion

REM Colors (using ANSI escape codes)
set "BLUE=[0;34m"
set "GREEN=[0;32m"
set "YELLOW=[1;33m"
set "RED=[0;31m"
set "NC=[0m"

REM Functions
:print_header
echo.
echo %BLUE%========================================%NC%
echo %BLUE%%~1%NC%
echo %BLUE%========================================%NC%
exit /b

:print_success
echo %GREEN%[OK] %~1%NC%
exit /b

:print_error
echo %RED%[ERROR] %~1%NC%
exit /b

:print_info
echo %YELLOW%[INFO] %~1%NC%
exit /b

REM Main command handling
if "%1"=="" goto show_help
if "%1"=="all" goto run_all_tests
if "%1"=="coverage" goto run_tests_with_coverage
if "%1"=="test" goto run_specific_test
if "%1"=="docker" goto run_docker_tests
if "%1"=="docker-bg" goto run_docker_tests_background
if "%1"=="logs" goto view_docker_logs
if "%1"=="stop" goto stop_docker_tests
if "%1"=="report" goto view_coverage_report
if "%1"=="report-docker" goto view_docker_coverage_report
if "%1"=="help" goto show_help
goto unknown_command

:run_all_tests
call :print_header "Running All Tests"
pytest tests/ -v
goto end

:run_tests_with_coverage
call :print_header "Running Tests with Coverage"
pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
call :print_success "Coverage report generated in htmlcov/index.html"
goto end

:run_specific_test
if "%2"=="" (
    call :print_error "Please provide test file or pattern"
    echo Usage: %0 test ^<file_or_pattern^>
    exit /b 1
)
call :print_header "Running Tests: %2"
pytest tests/ -k "%2" -v
goto end

:run_docker_tests
call :print_header "Running Tests in Docker"
docker-compose -f docker-compose.local.yml --profile test up test
goto end

:run_docker_tests_background
call :print_header "Running Tests in Docker (Background)"
docker-compose -f docker-compose.local.yml --profile test up -d test
call :print_info "Tests running in background. View logs with: docker-compose -f docker-compose.local.yml logs -f test"
goto end

:view_docker_logs
call :print_header "Viewing Docker Test Logs"
docker-compose -f docker-compose.local.yml logs -f test
goto end

:stop_docker_tests
call :print_header "Stopping Docker Tests"
docker-compose -f docker-compose.local.yml --profile test down
call :print_success "Docker test service stopped"
goto end

:view_coverage_report
call :print_header "Opening Coverage Report"
if exist "htmlcov\index.html" (
    start htmlcov\index.html
) else (
    call :print_error "Coverage report not found. Run tests with coverage first: %0 coverage"
)
goto end

:view_docker_coverage_report
call :print_header "Opening Docker Coverage Report"
if exist "coverage_reports\html\index.html" (
    start coverage_reports\html\index.html
) else (
    call :print_error "Coverage report not found. Run Docker tests first: %0 docker"
)
goto end

:show_help
echo.
echo %BLUE%SecureScribe Backend Test Runner%NC%
echo.
echo Usage: %0 ^<command^> [options]
echo.
echo Commands:
echo   all              Run all tests
echo   coverage         Run tests with coverage report
echo   test ^<pattern^>   Run specific tests matching pattern
echo   docker           Run tests in Docker
echo   docker-bg        Run tests in Docker (background)
echo   logs             View Docker test logs
echo   stop             Stop Docker tests
echo   report           Open coverage report (local)
echo   report-docker    Open coverage report (Docker)
echo   help             Show this help message
echo.
echo Examples:
echo   %0 all                    # Run all tests
echo   %0 coverage               # Run tests with coverage
echo   %0 test user              # Run tests matching 'user'
echo   %0 docker                 # Run tests in Docker
echo   %0 report                 # Open coverage report
echo.
goto end

:unknown_command
call :print_error "Unknown command: %1"
call :show_help
exit /b 1

:end
endlocal
