#!/usr/bin/env python3
"""
pydhis2 Comprehensive API Testing Demo
======================================

A comprehensive API testing script with data quality reports (HTML output).
This script tests all major pydhis2 endpoints and generates detailed reports.

Usage:
    py demo_test.py

Expected Output:
    - HTML quality report: dqr_demo_report.html
    - JSON summary: demo_test_results.json
    - CSV data files: analytics_data.csv, metadata_summary.csv
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from pydhis2 import get_client, DHIS2Config
    from pydhis2.core.types import AnalyticsQuery
    from pydhis2.dqr.metrics import DataQualityReporter
    import pandas as pd
    
    # Get client classes
    AsyncDHIS2Client, SyncDHIS2Client = get_client()
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please install pydhis2: pip install pydhis2")
    sys.exit(1)


class DemoTester:
    """Comprehensive demo tester for pydhis2"""
    
    def __init__(self, config: DHIS2Config):
        self.config = config
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
    def log_test_result(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test result"""
        self.results["tests"][test_name] = {
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        self.results["summary"]["total_tests"] += 1
        if success:
            self.results["summary"]["passed"] += 1
            print(f"✅ {test_name}: {message}")
        else:
            self.results["summary"]["failed"] += 1
            print(f"❌ {test_name}: {message}")
            
    def log_warning(self, test_name: str, message: str):
        """Log warning"""
        self.results["summary"]["warnings"] += 1
        print(f"⚠️ {test_name}: {message}")
        
    async def test_connection(self, client: AsyncDHIS2Client) -> bool:
        """Test DHIS2 connection"""
        try:
            response = await client.get("system/info")
            system_info = {
                "system_name": response.get("systemName", "Unknown"),
                "version": response.get("version", "Unknown"),
                "base_url": self.config.base_url
            }
            
            self.log_test_result(
                "Connection Test",
                True,
                f"Connected to {system_info['system_name']} v{system_info['version']}",
                system_info
            )
            return True
            
        except Exception as e:
            self.log_test_result("Connection Test", False, str(e))
            return False
            
    async def test_analytics_endpoint(self, client: AsyncDHIS2Client) -> Optional[pd.DataFrame]:
        """Test Analytics endpoint"""
        try:
            # Test multiple analytics queries
            queries = [
                {
                    "name": "ANC 1st Visit - Last 12 Months",
                    "query": AnalyticsQuery(
                        dx=["Uvn6LCg7dVU"],
                        ou="ImspTQPwCqd",
                        pe="LAST_12_MONTHS"
                    )
                },
                {
                    "name": "Multiple Indicators - This Year",
                    "query": AnalyticsQuery(
                        dx=["Uvn6LCg7dVU", "ReUHfIn0pTQ"],
                        ou="O6uvpzGd5pu",
                        pe="THIS_YEAR"
                    )
                }
            ]
            
            all_data = []
            for test_query in queries:
                try:
                    df = await client.analytics.to_pandas(test_query["query"])
                    if not df.empty:
                        df['query_name'] = test_query["name"]
                        all_data.append(df)
                        self.log_test_result(
                            f"Analytics - {test_query['name']}",
                            True,
                            f"Retrieved {len(df)} records"
                        )
                    else:
                        self.log_warning(
                            f"Analytics - {test_query['name']}",
                            "No data returned"
                        )
                        
                except Exception as e:
                    self.log_test_result(
                        f"Analytics - {test_query['name']}",
                        False,
                        str(e)
                    )
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                return combined_df
            else:
                return None
                
        except Exception as e:
            self.log_test_result("Analytics Endpoint", False, str(e))
            return None
            
    async def test_metadata_endpoint(self, client: AsyncDHIS2Client) -> Optional[Dict]:
        """Test Metadata endpoint"""
        try:
            # Test different metadata queries
            metadata_tests = [
                {
                    "name": "Data Elements",
                    "resource": "dataElements",
                    "params": {"paging": "false", "fields": "id,name,shortName"}
                },
                {
                    "name": "Organisation Units",
                    "resource": "organisationUnits",
                    "params": {"paging": "false", "fields": "id,name,level"}
                },
                {
                    "name": "Indicators",
                    "resource": "indicators",
                    "params": {"paging": "false", "fields": "id,name,indicatorType"}
                }
            ]
            
            metadata_summary = {}
            
            for test in metadata_tests:
                try:
                    response = await client.metadata.get(test["resource"], params=test["params"])
                    items = response.get(test["resource"], [])
                    count = len(items)
                    
                    metadata_summary[test["resource"]] = {
                        "count": count,
                        "sample": items[:3] if items else []
                    }
                    
                    self.log_test_result(
                        f"Metadata - {test['name']}",
                        True,
                        f"Retrieved {count} items"
                    )
                    
                except Exception as e:
                    self.log_test_result(
                        f"Metadata - {test['name']}",
                        False,
                        str(e)
                    )
            
            return metadata_summary
            
        except Exception as e:
            self.log_test_result("Metadata Endpoint", False, str(e))
            return None
            
    async def test_tracker_endpoint(self, client: AsyncDHIS2Client) -> Optional[Dict]:
        """Test Tracker endpoint"""
        try:
            # Get tracked entity types first
            te_types_response = await client.get("trackedEntityTypes", params={"paging": "false"})
            te_types = te_types_response.get("trackedEntityTypes", [])
            
            if not te_types:
                self.log_warning("Tracker Endpoint", "No tracked entity types found")
                return None
            
            # Test tracker events query
            try:
                events_response = await client.tracker.get_events(
                    page_size=10,
                    total_pages=False
                )
                
                event_count = len(events_response.get("instances", []))
                
                tracker_summary = {
                    "tracked_entity_types": len(te_types),
                    "sample_events": event_count
                }
                
                self.log_test_result(
                    "Tracker Events",
                    True,
                    f"Found {len(te_types)} TE types, retrieved {event_count} sample events"
                )
                
                return tracker_summary
                
            except Exception as e:
                self.log_test_result("Tracker Events", False, str(e))
                return {"tracked_entity_types": len(te_types), "sample_events": 0}
                
        except Exception as e:
            self.log_test_result("Tracker Endpoint", False, str(e))
            return None
            
    def generate_html_report(self, analytics_data: Optional[pd.DataFrame] = None) -> str:
        """Generate HTML quality report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>pydhis2 Demo Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-radius: 3px; }}
        .success {{ background: #d5f4e6; border-left: 4px solid #27ae60; }}
        .failure {{ background: #fadbd8; border-left: 4px solid #e74c3c; }}
        .warning {{ background: #fef9e7; border-left: 4px solid #f39c12; }}
        .data-preview {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 pydhis2 Demo Test Report</h1>
        <p>Generated on: {timestamp}</p>
        <p>DHIS2 Server: {server_url}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Test Summary</h2>
        <p><strong>Total Tests:</strong> {total_tests}</p>
        <p><strong>Passed:</strong> <span style="color: green;">{passed}</span></p>
        <p><strong>Failed:</strong> <span style="color: red;">{failed}</span></p>
        <p><strong>Warnings:</strong> <span style="color: orange;">{warnings}</span></p>
        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
    </div>
    
    <h2>🔍 Test Results</h2>
    {test_results_html}
    
    {data_preview_html}
</body>
</html>
        """
        
        # Generate test results HTML
        test_results_html = ""
        for test_name, result in self.results["tests"].items():
            css_class = "success" if result["success"] else "failure"
            test_results_html += f"""
            <div class="test-result {css_class}">
                <h3>{test_name}</h3>
                <p>{result['message']}</p>
                <small>Time: {result['timestamp']}</small>
            </div>
            """
        
        # Generate data preview HTML
        data_preview_html = ""
        if analytics_data is not None and not analytics_data.empty:
            data_preview_html = f"""
            <h2>📈 Data Preview</h2>
            <div class="data-preview">
                <h3>Analytics Data Sample</h3>
                {analytics_data.head(10).to_html(classes='data-table')}
                <p><em>Showing first 10 rows of {len(analytics_data)} total records</em></p>
            </div>
            """
        
        # Calculate success rate
        total = self.results["summary"]["total_tests"]
        passed = self.results["summary"]["passed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return html_template.format(
            timestamp=self.results["test_timestamp"],
            server_url=self.config.base_url,
            total_tests=total,
            passed=passed,
            failed=self.results["summary"]["failed"],
            warnings=self.results["summary"]["warnings"],
            success_rate=success_rate,
            test_results_html=test_results_html,
            data_preview_html=data_preview_html
        )
        
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting pydhis2 Comprehensive Demo Test")
        print("=" * 60)
        
        try:
            async with AsyncDHIS2Client(self.config) as client:
                # Test connection
                connection_ok = await self.test_connection(client)
                
                if not connection_ok:
                    print("Cannot proceed without a valid connection.")
                    return
                
                # Test all endpoints
                print("\n📊 Testing Analytics Endpoint...")
                analytics_data = await self.test_analytics_endpoint(client)
                
                print("\n🗂️ Testing Metadata Endpoint...")
                metadata_summary = await self.test_metadata_endpoint(client)
                
                print("\n👥 Testing Tracker Endpoint...")
                tracker_summary = await self.test_tracker_endpoint(client)
                
                # Save results
                await self.save_results(analytics_data, metadata_summary, tracker_summary)
                
                # Generate HTML report
                html_report = self.generate_html_report(analytics_data)
                
                # Save HTML report
                html_file = Path("dqr_demo_report.html")
                html_file.write_text(html_report, encoding="utf-8")
                
                print(f"\n📄 Reports generated:")
                print(f"   - HTML Report: {html_file.absolute()}")
                print(f"   - JSON Summary: demo_test_results.json")
                
                if analytics_data is not None:
                    print(f"   - Analytics Data: analytics_data.csv")
                
                if metadata_summary:
                    print(f"   - Metadata Summary: metadata_summary.json")
                
                print(f"\n✅ Demo test completed!")
                print(f"Success Rate: {self.results['summary']['passed']}/{self.results['summary']['total_tests']} tests passed")
                
        except Exception as e:
            print(f"Demo test failed: {e}")
            
    async def save_results(self, analytics_data, metadata_summary, tracker_summary):
        """Save test results to files"""
        # Save JSON results
        with open("demo_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Save analytics data if available
        if analytics_data is not None and not analytics_data.empty:
            analytics_data.to_csv("analytics_data.csv", index=False)
        
        # Save metadata summary if available
        if metadata_summary:
            with open("metadata_summary.json", "w", encoding="utf-8") as f:
                json.dump(metadata_summary, f, indent=2, ensure_ascii=False)


async def main():
    """Main demo function"""
    # Configuration for DHIS2 demo server
    config = DHIS2Config(
        base_url="https://play.dhis2.org",
        auth=("admin", "district")
    )
    
    tester = DemoTester(config)
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        # Fix for Windows asyncio event loop - use SelectorEventLoop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo test interrupted")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
