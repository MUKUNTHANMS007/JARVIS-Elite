import pytest
import datetime
import sys
import os

class ReportPlugin:
    def __init__(self):
        self.reports = []

    def pytest_runtest_logreport(self, report):
        # Capture the result of the test execution (or setup/teardown failure)
        if report.when == "call" or (report.when == "setup" and report.failed):
            self.reports.append(report)

def run_suite():
    print("--- JARVIS System Diagnostics & Automated Testing ---")
    
    # Ensure backend path is in sys.path
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
        
    plugin = ReportPlugin()
    # Run pytest programmatically pointing to the automated_testing directory
    pytest.main(["-q", "--tb=short", os.path.join(backend_path, "automated_testing")], plugins=[plugin])
    
    reports = plugin.reports
    tests_run = len(reports)
    failures = [r for r in reports if r.failed]
    
    failed_tests = []
    error_tests = []
    for r in failures:
        if r.when in ("setup", "teardown"):
            error_tests.append(r)
        else:
            failed_tests.append(r)
            
    was_successful = len(failures) == 0
    
    report_content = f"""# JARVIS Automated Test Report
Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
------------------------------------------------------------
## Summary
- **Tests Run**: {tests_run}
- **Failures**: {len(failed_tests)}
- **Errors**: {len(error_tests)}
- **Status**: {"PASSED" if was_successful else "FAILED"}

## Details
"""
    if was_successful:
        report_content += "✅ All systems functional. Tools and Agent logic are operating within parameters.\n"
    else:
        if failed_tests:
            report_content += "### Failures\n"
            for f in failed_tests:
                report_content += f"- **{f.nodeid}**: {f.longreprtext}\n"
        if error_tests:
            report_content += "### Errors\n"
            for e in error_tests:
                report_content += f"- **{e.nodeid}**: {e.longreprtext}\n"

    report_path = os.path.join(backend_path, 'automated_testing', 'test_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"Report generated: {report_path}")
    return was_successful

if __name__ == "__main__":
    run_suite()
