#!/usr/bin/env python3
"""
Generate comprehensive test report from pytest results.
This script parses JUnit XML and coverage XML to create a detailed report.
"""

import xml.etree.ElementTree as ET
import json
import sys
from pathlib import Path
from datetime import datetime


def parse_junit_xml(junit_path):
    """Parse JUnit XML test results."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    
    tests = int(root.get('tests', 0))
    failures = int(root.get('failures', 0))
    errors = int(root.get('errors', 0))
    skipped = int(root.get('skipped', 0))
    time = float(root.get('time', 0))
    
    passed = tests - failures - errors - skipped
    
    failed_tests = []
    for testcase in root.findall('.//testcase'):
        failure = testcase.find('failure')
        error = testcase.find('error')
        if failure is not None or error is not None:
            classname = testcase.get('classname', 'Unknown')
            name = testcase.get('name', 'Unknown')
            message = (failure or error).get('message', 'No message')
            failed_tests.append({
                'class': classname,
                'name': name,
                'message': message
            })
    
    return {
        'total': tests,
        'passed': passed,
        'failed': failures,
        'errors': errors,
        'skipped': skipped,
        'time': time,
        'failed_tests': failed_tests
    }


def parse_coverage_xml(coverage_path):
    """Parse coverage XML report."""
    tree = ET.parse(coverage_path)
    root = tree.getroot()
    
    line_rate = float(root.get('line-rate', 0)) * 100
    branch_rate = float(root.get('branch-rate', 0)) * 100
    
    packages = []
    for package in root.findall('.//package'):
        pkg_name = package.get('name', 'Unknown')
        pkg_line_rate = float(package.get('line-rate', 0)) * 100
        pkg_branch_rate = float(package.get('branch-rate', 0)) * 100
        
        packages.append({
            'name': pkg_name,
            'line_rate': pkg_line_rate,
            'branch_rate': pkg_branch_rate
        })
    
    return {
        'line_rate': line_rate,
        'branch_rate': branch_rate,
        'packages': packages
    }


def generate_markdown_report(junit_data, coverage_data):
    """Generate markdown report."""
    report = []
    report.append("# Test Execution Report\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    # Test Results Summary
    report.append("## Test Results Summary\n")
    report.append(f"| Metric | Count |")
    report.append(f"|--------|-------|")
    report.append(f"| Total Tests | {junit_data['total']} |")
    report.append(f"| ✅ Passed | {junit_data['passed']} |")
    report.append(f"| ❌ Failed | {junit_data['failed']} |")
    report.append(f"| ⚠️ Errors | {junit_data['errors']} |")
    report.append(f"| ⏭️ Skipped | {junit_data['skipped']} |")
    report.append(f"| ⏱️ Duration | {junit_data['time']:.2f}s |")
    report.append("")
    
    # Coverage Summary
    report.append("## Coverage Summary\n")
    report.append(f"| Metric | Coverage |")
    report.append(f"|--------|----------|")
    report.append(f"| Line Coverage | {coverage_data['line_rate']:.1f}% |")
    report.append(f"| Branch Coverage | {coverage_data['branch_rate']:.1f}% |")
    report.append("")
    
    # Coverage by Package
    if coverage_data['packages']:
        report.append("## Coverage by Package\n")
        report.append(f"| Package | Line Rate | Branch Rate |")
        report.append(f"|---------|-----------|-------------|")
        for pkg in sorted(coverage_data['packages'], key=lambda x: x['line_rate'], reverse=True):
            report.append(f"| {pkg['name']} | {pkg['line_rate']:.1f}% | {pkg['branch_rate']:.1f}% |")
        report.append("")
    
    # Failed Tests Details
    if junit_data['failed_tests']:
        report.append("## Failed Tests\n")
        for i, test in enumerate(junit_data['failed_tests'], 1):
            report.append(f"### {i}. {test['class']}::{test['name']}\n")
            report.append(f"```\n{test['message']}\n```\n")
    
    # Status
    report.append("## Status\n")
    if junit_data['failed'] == 0 and junit_data['errors'] == 0:
        report.append("✅ **All tests passed!**\n")
    else:
        report.append(f"❌ **{junit_data['failed'] + junit_data['errors']} test(s) failed**\n")
    
    if coverage_data['line_rate'] >= 80:
        report.append(f"✅ **Coverage meets threshold (>80%): {coverage_data['line_rate']:.1f}%**\n")
    else:
        report.append(f"⚠️ **Coverage below threshold (<80%): {coverage_data['line_rate']:.1f}%**\n")
    
    return "\n".join(report)


def generate_json_report(junit_data, coverage_data):
    """Generate JSON report."""
    return {
        'timestamp': datetime.now().isoformat(),
        'tests': junit_data,
        'coverage': coverage_data
    }


def main():
    """Main entry point."""
    junit_path = Path('coverage_reports/junit.xml')
    coverage_path = Path('coverage_reports/coverage.xml')
    
    if not junit_path.exists():
        print(f"Error: {junit_path} not found", file=sys.stderr)
        return 1
    
    if not coverage_path.exists():
        print(f"Error: {coverage_path} not found", file=sys.stderr)
        return 1
    
    # Parse reports
    junit_data = parse_junit_xml(junit_path)
    coverage_data = parse_coverage_xml(coverage_path)
    
    # Generate reports
    markdown_report = generate_markdown_report(junit_data, coverage_data)
    json_report = generate_json_report(junit_data, coverage_data)
    
    # Write markdown report
    report_path = Path('coverage_reports/TEST_REPORT.md')
    report_path.write_text(markdown_report)
    print(f"✅ Markdown report written to {report_path}")
    
    # Write JSON report
    json_path = Path('coverage_reports/test_report.json')
    json_path.write_text(json.dumps(json_report, indent=2))
    print(f"✅ JSON report written to {json_path}")
    
    # Print summary to stdout
    print("\n" + markdown_report)
    
    # Return exit code based on test results
    if junit_data['failed'] > 0 or junit_data['errors'] > 0:
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
