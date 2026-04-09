import unittest
import sys
import os
import datetime

def run_suite():
    """Run all tests in the automated_testing directory and generate a report."""
    print("--- JARVIS System Diagnostics & Automated Testing ---")
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='d:\\JARVIS\\backend\\automated_testing', pattern='test_*.py')
    
    # Run tests and capture results
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate Report
    report_content = f"""# JARVIS Automated Test Report
Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
------------------------------------------------------------
## Summary
- **Tests Run**: {result.testsRun}
- **Failures**: {len(result.failures)}
- **Errors**: {len(result.errors)}
- **Status**: {"PASSED" if result.wasSuccessful() else "FAILED"}

## Details
"""
    if result.wasSuccessful():
        report_content += "✅ All systems functional. Tools and Agent logic are operating within parameters.\n"
    else:
        if result.failures:
            report_content += "### Failures\n"
            for f in result.failures:
                report_content += f"- **{f[0]}**: {f[1]}\n"
        if result.errors:
            report_content += "### Errors\n"
            for e in result.errors:
                report_content += f"- **{e[0]}**: {e[1]}\n"

    # Save report to artifacts directory (or current directory)
    report_path = 'd:\\JARVIS\\backend\\automated_testing\\test_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"Report generated: {report_path}")
    return result.wasSuccessful()

if __name__ == "__main__":
    run_suite()
