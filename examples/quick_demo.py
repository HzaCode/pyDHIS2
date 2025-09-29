#!/usr/bin/env python3
"""
pydhis2 Quick Demo
==================

A basic functionality demo with connection testing and data analysis.
This script demonstrates the core features of pydhis2 in a simple, 
easy-to-understand format.

Usage:
    py quick_demo.py

Expected Output:
    - Connection test results
    - Analytics data retrieval and preview
    - Basic statistics and visualizations
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

try:
    from pydhis2 import get_client, DHIS2Config
    from pydhis2.core.types import AnalyticsQuery
    import pandas as pd
    
    # Get client classes
    AsyncDHIS2Client, SyncDHIS2Client = get_client()
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please install pydhis2: pip install pydhis2")
    sys.exit(1)


def print_header():
    """Print demo header"""
    print("=" * 60)
    print("pydhis2 Quick Demo")
    print("=" * 60)
    print()


def print_separator():
    """Print section separator"""
    print("-" * 60)


def create_bar_chart(value: int, max_value: int, width: int = 40) -> str:
    """Create a simple ASCII bar chart"""
    if max_value == 0:
        return ""
    
    bar_length = int((value / max_value) * width)
    return "█" * bar_length


async def test_connection(client: AsyncDHIS2Client) -> bool:
    """Test DHIS2 connection"""
    print("   Step 1: Testing basic server connectivity...")
    
    try:
        # First, test basic connectivity
        print(f"   Trying base URL: {client.config.base_url}")
        response = await client.get("")
        print(f"   Server responded! Response type: {type(response)}")
        
        # Check if it's a dict (JSON response) or something else
        if isinstance(response, dict):
            print("   Got JSON response - this looks like an API endpoint")
            if response.get("status") == "OK" or "version" in response:
                system_name = response.get("systemName", "DHIS2 Demo")
                version = response.get("version", "Unknown")
                print("   Connection successful!")
                print(f"   System: {system_name}")
                print(f"   Version: {version}")
                return True
            else:
                print(f"   JSON response keys: {list(response.keys())}")
        else:
            print("   Got non-JSON response (probably HTML page)")
        
        # Step 2: Try common DHIS2 API endpoints
        print("   Step 2: Testing DHIS2 API endpoints...")
        
        api_endpoints_to_test = [
            "api/system/info",
            "api/me", 
            "dhis-web-commons/security/login.action",
            "api"
        ]
        
        for endpoint in api_endpoints_to_test:
            try:
                print(f"   Trying: {client.config.base_url}/{endpoint}")
                test_response = await client.get(endpoint)
                
                if isinstance(test_response, dict):
                    if "version" in test_response or "systemName" in test_response:
                        system_name = test_response.get("systemName", "DHIS2")
                        version = test_response.get("version", "Unknown")
                        print("   Found working API endpoint!")
                        print(f"   System: {system_name}")
                        print(f"   Version: {version}")
                        return True
                    elif test_response.get("status") == "OK":
                        print("   API endpoint responded with OK status")
                        return True
                    else:
                        print(f"   Got response: {list(test_response.keys())[:5]}")
                        
            except Exception as e:
                print(f"   Failed {endpoint}: {str(e)[:100]}")
                continue
        
        print("   Could not find working API endpoint, but server is reachable")
        return False
            
    except Exception as e:
        print(f"   Connection completely failed: {e}")
        return False


async def fetch_analytics_data(client: AsyncDHIS2Client) -> Optional[pd.DataFrame]:
    """Fetch sample analytics data"""
    try:
        # Define query using available data elements from the server
        # Note: Using generic data element IDs that should exist in demo servers
        query = AnalyticsQuery(
            dx=["b6mCG9sphIT"],   # ANC 1 Outlier Threshold (from Data Quality Demo)
            ou="qzGX4XdWufs",    # A-1 District Hospital (from Data Quality Demo) 
            pe="2023"            # Year 2023 (this format worked in our test!)
        )
        
        # Fetch data and convert to DataFrame
        df = await client.analytics.to_pandas(query)
        
        if not df.empty:
            print(f"Retrieved {len(df)} data records")
            return df
        else:
            print("No data found for the specified query")
            return None
            
    except Exception as e:
        print(f"Data fetch failed: {e}")
        return None


def analyze_data(df: pd.DataFrame):
    """Analyze and display data statistics"""
    if df.empty:
        print("No data to analyze")
        return
    
    # Basic statistics
    total_records = len(df)
    if 'value' in df.columns:
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        total_sum = df['value'].sum()
        average = df['value'].mean()
        maximum = df['value'].max()
        minimum = df['value'].min()
        
        print(f"   Total records: {total_records}")
        print(f"   Sum of values: {total_sum:,}")
        print(f"   Average: {average:.1f}")
        print(f"   Maximum: {maximum}")
        print(f"   Minimum: {minimum}")
    else:
        print(f"   Total records: {total_records}")


def display_trends(df: pd.DataFrame):
    """Display monthly trends as ASCII chart"""
    if df.empty or 'period' not in df.columns or 'value' not in df.columns:
        print("No trend data available")
        return
    
    # Convert values to numeric
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    
    # Group by period and sum values
    trends = df.groupby('period')['value'].sum().sort_index()
    
    if trends.empty:
        print("No trend data available")
        return
    
    max_value = trends.max()
    
    for period, value in trends.head(6).items():  # Show first 6 periods
        bar = create_bar_chart(int(value), int(max_value))
        print(f"   {period}: {bar} {int(value)}")


async def main():
    """Main demo function"""
    print_header()
    
    # Configuration for DHIS2 demo server
    # Configuration for DHIS2 server
    # You can change these settings to use your own DHIS2 server
    
    import os
    
    # Check for environment variables first
    dhis2_url = os.getenv("DHIS2_URL")
    dhis2_username = os.getenv("DHIS2_USERNAME", "admin")
    dhis2_password = os.getenv("DHIS2_PASSWORD", "district")
    
    if dhis2_url:
        print(f"Using DHIS2 server from environment: {dhis2_url}")
        demo_servers = [dhis2_url]
    else:
        print("No DHIS2_URL environment variable found.")
        print("Using verified working DHIS2 demo servers...")
        demo_servers = [
            "https://demos.dhis2.org/dq",      # Data Quality Demo - DHIS2 v2.38.4.3 (has ANC data!)
            "https://emis.dhis2.org/demo",      # EMIS Demo - DHIS2 v2.40.4.1 (education data)
        ]
    
    print("\nTo use your own DHIS2 server:")
    print("1. Set environment variables:")
    print("   set DHIS2_URL=https://your-dhis2-server.com")
    print("   set DHIS2_USERNAME=your_username")
    print("   set DHIS2_PASSWORD=your_password")
    print("2. Or edit this script directly")
    print("\nTesting DHIS2 server(s)...")
    
    for server_url in demo_servers:
        print(f"\n=== Testing: {server_url} ===")
        
        # Use correct credentials for each server
        if "demos.dhis2.org/dq" in server_url:
            username, password = "demo", "District1#"
        else:
            username, password = dhis2_username, dhis2_password
            
        config = DHIS2Config(
            base_url=server_url,
            auth=(username, password)
        )
        
        try:
            async with AsyncDHIS2Client(config) as client:
                # Test connection
                connection_ok = await test_connection(client)
                
                if connection_ok:
                    print(f"Found working server: {server_url}")
                    # Continue with the rest of the demo
                    break
                else:
                    print(f"Server not working: {server_url}")
                    continue
                    
        except Exception as e:
            print(f"Error with {server_url}: {e}")
            continue
    else:
        print("No working DHIS2 server found")
        return
    
    # If we get here, we have a working connection
    try:
        async with AsyncDHIS2Client(config) as client:
            
            # 2. Fetch analytics data
            print("2. Querying Analytics data...")
            df = await fetch_analytics_data(client)
            print()
            
            if df is not None and not df.empty:
                # 3. Display data preview
                print("3. Data preview:")
                print_separator()
                print(df.head().to_string(index=False))
                print()
                
                # 4. Show statistics
                print("4. Data statistics:")
                print_separator()
                analyze_data(df)
                print()
                
                # 5. Show trends
                print("5. Monthly trends:")
                print_separator()
                display_trends(df)
                print()
            else:
                print("3. No data available for analysis")
                print()
            
            print("Demo completed successfully!")
            
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the demo
    try:
        # Fix for Windows asyncio event loop - use SelectorEventLoop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
