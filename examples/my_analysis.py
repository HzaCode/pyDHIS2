#!/usr/bin/env python3
"""
pydhis2 Custom Analysis Template
================================

Template for custom analysis projects using pydhis2.
This script provides a flexible framework for your own DHIS2 data analysis.

Usage:
    py my_analysis.py

Customization:
    1. Modify the configuration section with your DHIS2 server details
    2. Update the indicators and organization units in the query section
    3. Add your custom analysis functions
    4. Customize the output format and file names
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from pydhis2 import get_client, DHIS2Config
    from pydhis2.core.types import AnalyticsQuery
    import pandas as pd
    import numpy as np
    
    # Get client classes
    AsyncDHIS2Client, SyncDHIS2Client = get_client()
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please install pydhis2: pip install pydhis2")
    sys.exit(1)


class CustomAnalyzer:
    """Custom DHIS2 data analyzer"""
    
    def __init__(self, config: DHIS2Config):
        self.config = config
        self.results = {}
        
    def print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
        
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{'-'*40}")
        print(f"{title}")
        print(f"{'-'*40}")
        
    async def test_connection(self, client: AsyncDHIS2Client) -> bool:
        """Test connection to DHIS2 server"""
        try:
            response = await client.get("system/info")
            system_name = response.get("systemName", "DHIS2")
            version = response.get("version", "Unknown")
            
            print(f"✅ Connected to {system_name} v{version}")
            print(f"🌐 Server: {self.config.base_url}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    async def fetch_analytics_data(self, client: AsyncDHIS2Client, 
                                  indicators: List[str], 
                                  org_units: str, 
                                  periods: str) -> Optional[pd.DataFrame]:
        """Fetch analytics data with custom parameters"""
        try:
            query = AnalyticsQuery(
                dx=indicators,
                ou=org_units,
                pe=periods
            )
            
            df = await client.analytics.to_pandas(query)
            
            if not df.empty:
                print(f"✅ Retrieved {len(df)} data records")
                return df
            else:
                print("⚠️ No data found for the specified query")
                return None
                
        except Exception as e:
            print(f"❌ Data fetch failed: {e}")
            return None
            
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform custom data analysis"""
        if df.empty:
            return {}
        
        analysis_results = {}
        
        # Convert value column to numeric
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            # Basic statistics
            analysis_results['basic_stats'] = {
                'total_records': len(df),
                'mean': df['value'].mean(),
                'median': df['value'].median(),
                'std': df['value'].std(),
                'min': df['value'].min(),
                'max': df['value'].max()
            }
            
            # Time series analysis (if period column exists)
            if 'period' in df.columns:
                analysis_results['time_series'] = self.analyze_time_series(df)
            
            # Geographic analysis (if organisationUnit column exists)
            if 'organisationUnit' in df.columns:
                analysis_results['geographic'] = self.analyze_geographic(df)
                
        return analysis_results
        
    def analyze_time_series(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze time series trends"""
        # Group by period and calculate trends
        period_stats = df.groupby('period')['value'].agg(['mean', 'count']).reset_index()
        period_stats = period_stats.sort_values('period')
        
        # Calculate simple trend
        if len(period_stats) >= 2:
            x = np.arange(len(period_stats))
            y = period_stats['mean'].values
            
            # Linear regression for trend
            if len(x) > 1:
                slope, intercept = np.polyfit(x, y, 1)
                trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
            else:
                trend_direction = "insufficient_data"
        else:
            trend_direction = "insufficient_data"
            
        return {
            'periods_analyzed': len(period_stats),
            'trend_direction': trend_direction,
            'period_stats': period_stats.to_dict('records')
        }
        
    def analyze_geographic(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze geographic distribution"""
        # Group by organization unit
        org_stats = df.groupby('organisationUnit')['value'].agg(['mean', 'count']).reset_index()
        org_stats = org_stats.sort_values('mean', ascending=False)
        
        return {
            'org_units_analyzed': len(org_stats),
            'top_performers': org_stats.head(5).to_dict('records'),
            'bottom_performers': org_stats.tail(5).to_dict('records')
        }
        
    def generate_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate insights from analysis results"""
        insights = []
        
        # Basic statistics insights
        basic_stats = analysis_results.get('basic_stats', {})
        if basic_stats:
            mean_val = basic_stats.get('mean', 0)
            if mean_val >= 80:
                insights.append(f"📈 Strong performance with average of {mean_val:.1f}%")
            elif mean_val >= 60:
                insights.append(f"📊 Moderate performance with average of {mean_val:.1f}%")
            else:
                insights.append(f"📉 Low performance with average of {mean_val:.1f}%")
                
        # Time series insights
        time_series = analysis_results.get('time_series', {})
        if time_series:
            trend = time_series.get('trend_direction', 'unknown')
            if trend == 'increasing':
                insights.append("📈 Positive trend over time")
            elif trend == 'decreasing':
                insights.append("📉 Declining trend - needs attention")
            else:
                insights.append("📊 Stable trend over time")
                
        # Geographic insights
        geographic = analysis_results.get('geographic', {})
        if geographic:
            org_count = geographic.get('org_units_analyzed', 0)
            insights.append(f"🌍 Analysis covers {org_count} organization units")
            
        return insights
        
    def save_results(self, df: pd.DataFrame, analysis_results: Dict[str, Any], 
                    insights: List[str]):
        """Save analysis results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data
        if not df.empty:
            data_file = f"analysis_data_{timestamp}.csv"
            df.to_csv(data_file, index=False)
            print(f"💾 Data saved: {data_file}")
        
        # Save analysis results
        import json
        results_file = f"analysis_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'server': self.config.base_url,
                'analysis_results': analysis_results,
                'insights': insights
            }, f, indent=2, ensure_ascii=False)
        print(f"📊 Results saved: {results_file}")
        
        # Generate summary report
        self.generate_report(analysis_results, insights, timestamp)
        
    def generate_report(self, analysis_results: Dict[str, Any], 
                       insights: List[str], timestamp: str):
        """Generate markdown report"""
        report_content = f"""# DHIS2 Data Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Server:** {self.config.base_url}

## Summary

"""
        
        # Add basic statistics
        basic_stats = analysis_results.get('basic_stats', {})
        if basic_stats:
            report_content += f"""### Data Overview
- **Total Records:** {basic_stats.get('total_records', 0):,}
- **Average Value:** {basic_stats.get('mean', 0):.2f}
- **Value Range:** {basic_stats.get('min', 0):.1f} - {basic_stats.get('max', 0):.1f}
- **Standard Deviation:** {basic_stats.get('std', 0):.2f}

"""
        
        # Add time series analysis
        time_series = analysis_results.get('time_series', {})
        if time_series:
            report_content += f"""### Time Series Analysis
- **Periods Analyzed:** {time_series.get('periods_analyzed', 0)}
- **Trend Direction:** {time_series.get('trend_direction', 'Unknown')}

"""
        
        # Add geographic analysis
        geographic = analysis_results.get('geographic', {})
        if geographic:
            report_content += f"""### Geographic Analysis
- **Organization Units:** {geographic.get('org_units_analyzed', 0)}

"""
        
        # Add insights
        if insights:
            report_content += "### Key Insights\n\n"
            for insight in insights:
                report_content += f"- {insight}\n"
            report_content += "\n"
        
        report_content += """### Recommendations

1. **Data Quality:** Review data collection processes for completeness
2. **Performance:** Focus on areas with declining trends
3. **Geographic:** Compare high and low performing units for best practices
4. **Monitoring:** Set up regular monitoring for key indicators

---
*Generated by pydhis2 Custom Analysis Template*
"""
        
        report_file = f"analysis_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"📄 Report saved: {report_file}")
        
    async def run_analysis(self, indicators: List[str], org_units: str, periods: str):
        """Run the complete analysis"""
        self.print_header("🔍 Custom DHIS2 Data Analysis")
        
        try:
            async with AsyncDHIS2Client(self.config) as client:
                # Test connection
                self.print_section("Connection Test")
                if not await self.test_connection(client):
                    return
                
                # Fetch data
                self.print_section("Data Retrieval")
                print(f"📊 Indicators: {', '.join(indicators)}")
                print(f"🏢 Organization Units: {org_units}")
                print(f"📅 Periods: {periods}")
                
                df = await self.fetch_analytics_data(client, indicators, org_units, periods)
                
                if df is None or df.empty:
                    print("❌ No data available for analysis")
                    return
                
                # Analyze data
                self.print_section("Data Analysis")
                analysis_results = self.analyze_data(df)
                
                # Generate insights
                self.print_section("Insights")
                insights = self.generate_insights(analysis_results)
                
                for insight in insights:
                    print(f"  {insight}")
                
                # Save results
                self.print_section("Saving Results")
                self.save_results(df, analysis_results, insights)
                
                self.print_header("✅ Analysis Complete!")
                
        except Exception as e:
            print(f"Analysis failed: {e}")


async def main():
    """Main function - Customize this section for your analysis"""
    
    # ========================================
    # CONFIGURATION SECTION - CUSTOMIZE HERE
    # ========================================
    
    # DHIS2 server configuration
    config = DHIS2Config(
        base_url="https://play.dhis2.org",  # Change to your DHIS2 server
        auth=("admin", "district")  # Change to your credentials
    )
    
    # Analysis parameters - CUSTOMIZE THESE
    indicators = [
        "Uvn6LCg7dVU",  # ANC 1st visit coverage
        "ReUHfIn0pTQ"   # ANC 4th visit coverage
        # Add more indicator IDs here
    ]
    
    org_units = "ImspTQPwCqd"  # Sierra Leone - Change to your organization unit
    periods = "LAST_12_MONTHS"  # Change to your desired period
    
    # ========================================
    # RUN ANALYSIS
    # ========================================
    
    analyzer = CustomAnalyzer(config)
    await analyzer.run_analysis(indicators, org_units, periods)


if __name__ == "__main__":
    """
    To customize this analysis:
    
    1. Update the configuration section with your DHIS2 server details
    2. Modify the indicators list with your specific indicator IDs
    3. Change org_units to your target organization unit(s)
    4. Adjust periods to your desired time range
    5. Add custom analysis functions if needed
    
    Example customizations:
    - indicators = ["your_indicator_id1", "your_indicator_id2"]
    - org_units = "your_org_unit_id"
    - periods = "2023;2024" or "LAST_6_MONTHS" or "THIS_YEAR"
    """
    try:
        # Fix for Windows asyncio event loop - use SelectorEventLoop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAnalysis interrupted")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
