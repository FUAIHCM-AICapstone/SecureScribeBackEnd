#!/usr/bin/env python3
"""
Generate coverage badge SVG for README.
This script creates a badge showing the current test coverage percentage.
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path


def get_coverage_percentage(coverage_path):
    """Extract coverage percentage from coverage XML."""
    tree = ET.parse(coverage_path)
    root = tree.getroot()
    line_rate = float(root.get('line-rate', 0)) * 100
    return line_rate


def get_badge_color(coverage):
    """Get badge color based on coverage percentage."""
    if coverage >= 90:
        return '#4c1'  # Green
    elif coverage >= 80:
        return '#dfb317'  # Yellow
    elif coverage >= 70:
        return '#fe7d37'  # Orange
    else:
        return '#e05d44'  # Red


def generate_badge_svg(coverage):
    """Generate SVG badge."""
    color = get_badge_color(coverage)
    coverage_str = f"{coverage:.1f}%"
    
    # SVG template
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="140" height="20" role="img" aria-label="coverage: {coverage_str}">
    <title>coverage: {coverage_str}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb"/>
        <stop offset="1" stop-color="#999"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="140" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="93" height="20" fill="#555"/>
        <rect x="93" width="47" height="20" fill="{color}"/>
        <rect width="140" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="475" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="830">coverage</text>
        <text x="475" y="140" transform="scale(.1)" fill="#fff" textLength="830">coverage</text>
        <text aria-hidden="true" x="1155" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="370">{coverage_str}</text>
        <text x="1155" y="140" transform="scale(.1)" fill="#fff" textLength="370">{coverage_str}</text>
    </g>
</svg>'''
    
    return svg


def main():
    """Main entry point."""
    coverage_path = Path('coverage_reports/coverage.xml')
    
    if not coverage_path.exists():
        print(f"Error: {coverage_path} not found", file=sys.stderr)
        return 1
    
    # Get coverage percentage
    coverage = get_coverage_percentage(coverage_path)
    
    # Generate badge
    badge_svg = generate_badge_svg(coverage)
    
    # Write badge
    badge_path = Path('coverage_reports/coverage-badge.svg')
    badge_path.write_text(badge_svg)
    print(f"✅ Coverage badge written to {badge_path}")
    print(f"Coverage: {coverage:.1f}%")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
