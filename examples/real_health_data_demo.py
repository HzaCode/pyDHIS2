#!/usr/bin/env python3
"""
pydhis2 Real Health Data Analysis Demo
======================================

Health data analysis with quality metrics and insights.
This script demonstrates real-world health data analysis workflows
using pydhis2 with comprehensive data quality assessment.

Usage:
    py real_health_data_demo.py

Expected Output:
    - Health indicators analysis
    - Data quality metrics
    - Geographic analysis
    - Time series trends
    - Summary reports and visualizations
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    from pydhis2 import get_client, DHIS2Config
    from pydhis2.core.types import AnalyticsQuery
    from pydhis2.dqr.metrics import DataQualityReporter
    import pandas as pd
    import numpy as np
    
    # Get client classes
    AsyncDHIS2Client, SyncDHIS2Client = get_client()
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please install pydhis2: pip install pydhis2")
    sys.exit(1)


class HealthDataAnalyzer:
    """Real health data analyzer with DQR capabilities"""
    
    def __init__(self, config: DHIS2Config):
        self.config = config
        self.analysis_results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "indicators": {},
            "quality_metrics": {},
            "geographic_analysis": {},
            "time_series": {},
            "insights": []
        }
        
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
        
    def print_subheader(self, title: str):
        """Print subsection header"""
        print(f"\n{'-'*40}")
        print(f"{title}")
        print(f"{'-'*40}")
        
    async def get_health_indicators(self, client: AsyncDHIS2Client) -> List[Dict]:
        """Get key health indicators"""
        try:
            # Common health indicators
            health_indicators = [
                {
                    "id": "Uvn6LCg7dVU",
                    "name": "ANC 1st visit coverage",
                    "category": "Maternal Health"
                },
                {
                    "id": "ReUHfIn0pTQ", 
                    "name": "ANC 4th visit coverage",
                    "category": "Maternal Health"
                },
                {
                    "id": "dwEq7wi6nXV",
                    "name": "BCG coverage",
                    "category": "Immunization"
                },
                {
                    "id": "Rigf2d2Zbjp",
                    "name": "DPT3 coverage",
                    "category": "Immunization"
                }
            ]
            
            # Verify indicators exist
            verified_indicators = []
            for indicator in health_indicators:
                try:
                    response = await client.get(f"indicators/{indicator['id']}")
                    if response.get("id") == indicator["id"]:
                        verified_indicators.append(indicator)
                        print(f"✅ Found indicator: {indicator['name']}")
                    else:
                        print(f"⚠️ Indicator not found: {indicator['name']}")
                except:
                    print(f"⚠️ Could not verify indicator: {indicator['name']}")
            
            return verified_indicators if verified_indicators else health_indicators
            
        except Exception as e:
            print(f"❌ Error getting health indicators: {e}")
            return []
            
    async def analyze_indicator_performance(self, client: AsyncDHIS2Client, 
                                          indicators: List[Dict]) -> pd.DataFrame:
        """Analyze health indicator performance"""
        self.print_subheader("Indicator Performance Analysis")
        
        all_data = []
        
        for indicator in indicators[:2]:  # Limit to first 2 for demo
            try:
                # Query data for the last 24 months
                query = AnalyticsQuery(
                    dx=[indicator["id"]],
                    ou="ImspTQPwCqd",  # Sierra Leone
                    pe="LAST_24_MONTHS"
                )
                
                df = await client.analytics.to_pandas(query)
                
                if not df.empty:
                    df['indicator_name'] = indicator['name']
                    df['indicator_category'] = indicator['category']
                    all_data.append(df)
                    
                    # Calculate basic statistics
                    if 'value' in df.columns:
                        df['value'] = pd.to_numeric(df['value'], errors='coerce')
                        stats = {
                            "mean": df['value'].mean(),
                            "median": df['value'].median(),
                            "std": df['value'].std(),
                            "min": df['value'].min(),
                            "max": df['value'].max(),
                            "trend": self.calculate_trend(df)
                        }
                        
                        self.analysis_results["indicators"][indicator['name']] = stats
                        
                        print(f"📊 {indicator['name']}:")
                        print(f"   Average: {stats['mean']:.1f}%")
                        print(f"   Range: {stats['min']:.1f}% - {stats['max']:.1f}%")
                        print(f"   Trend: {stats['trend']}")
                
            except Exception as e:
                print(f"❌ Error analyzing {indicator['name']}: {e}")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()
            
    def calculate_trend(self, df: pd.DataFrame) -> str:
        """Calculate simple trend analysis"""
        if 'value' not in df.columns or len(df) < 2:
            return "Insufficient data"
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['value']).sort_values('period')
        
        if len(df) < 2:
            return "Insufficient data"
        
        # Simple linear trend
        x = np.arange(len(df))
        y = df['value'].values
        
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            if slope > 1:
                return "📈 Improving"
            elif slope < -1:
                return "📉 Declining"
            else:
                return "📊 Stable"
        
        return "No trend"
        
    async def assess_data_quality(self, df: pd.DataFrame) -> Dict:
        """Assess data quality metrics"""
        self.print_subheader("Data Quality Assessment")
        
        if df.empty:
            print("⚠️ No data available for quality assessment")
            return {}
        
        # Convert value column to numeric
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        quality_metrics = {
            "completeness": {
                "total_expected": len(df),
                "total_available": len(df.dropna(subset=['value'])),
                "completeness_rate": len(df.dropna(subset=['value'])) / len(df) * 100 if len(df) > 0 else 0
            },
            "consistency": {
                "outliers_count": 0,
                "negative_values": 0,
                "extreme_values": 0
            },
            "timeliness": {
                "recent_data_points": 0,
                "data_recency": "Unknown"
            }
        }
        
        if 'value' in df.columns:
            values = df['value'].dropna()
            
            if len(values) > 0:
                # Check for outliers (values beyond 3 standard deviations)
                mean_val = values.mean()
                std_val = values.std()
                outliers = values[(values < mean_val - 3*std_val) | (values > mean_val + 3*std_val)]
                quality_metrics["consistency"]["outliers_count"] = len(outliers)
                
                # Check for negative values (unusual for health indicators)
                negative_count = len(values[values < 0])
                quality_metrics["consistency"]["negative_values"] = negative_count
                
                # Check for extreme values (>100% for coverage indicators)
                extreme_count = len(values[values > 100])
                quality_metrics["consistency"]["extreme_values"] = extreme_count
        
        # Check data recency
        if 'period' in df.columns:
            periods = df['period'].dropna()
            if len(periods) > 0:
                latest_period = max(periods)
                current_period = datetime.now().strftime("%Y%m")
                
                # Simple recency check (assuming YYYYMM format)
                try:
                    latest_year = int(latest_period[:4])
                    current_year = datetime.now().year
                    
                    if current_year - latest_year <= 1:
                        quality_metrics["timeliness"]["data_recency"] = "Recent"
                        quality_metrics["timeliness"]["recent_data_points"] = len(periods)
                    else:
                        quality_metrics["timeliness"]["data_recency"] = "Outdated"
                except:
                    quality_metrics["timeliness"]["data_recency"] = "Unknown format"
        
        self.analysis_results["quality_metrics"] = quality_metrics
        
        # Print quality assessment
        comp_rate = quality_metrics["completeness"]["completeness_rate"]
        print(f"📋 Data Completeness: {comp_rate:.1f}%")
        print(f"🔍 Data Consistency:")
        print(f"   Outliers: {quality_metrics['consistency']['outliers_count']}")
        print(f"   Negative values: {quality_metrics['consistency']['negative_values']}")
        print(f"   Values >100%: {quality_metrics['consistency']['extreme_values']}")
        print(f"⏰ Data Recency: {quality_metrics['timeliness']['data_recency']}")
        
        return quality_metrics
        
    async def geographic_analysis(self, client: AsyncDHIS2Client, 
                                 indicators: List[Dict]) -> Dict:
        """Analyze geographic distribution"""
        self.print_subheader("Geographic Analysis")
        
        if not indicators:
            print("⚠️ No indicators available for geographic analysis")
            return {}
        
        try:
            # Get organization units at different levels
            org_units_response = await client.get("organisationUnits", params={
                "paging": "false",
                "fields": "id,name,level,parent",
                "filter": "level:le:3"  # Up to level 3
            })
            
            org_units = org_units_response.get("organisationUnits", [])
            
            if not org_units:
                print("⚠️ No organization units found")
                return {}
            
            # Analyze by organization unit levels
            levels_analysis = {}
            for level in [1, 2, 3]:
                level_ous = [ou for ou in org_units if ou.get("level") == level]
                levels_analysis[f"level_{level}"] = {
                    "count": len(level_ous),
                    "sample": [ou["name"] for ou in level_ous[:3]]
                }
            
            print(f"🌍 Organization Structure:")
            for level, data in levels_analysis.items():
                print(f"   Level {level[-1]}: {data['count']} units")
                if data['sample']:
                    print(f"      Examples: {', '.join(data['sample'])}")
            
            self.analysis_results["geographic_analysis"] = levels_analysis
            return levels_analysis
            
        except Exception as e:
            print(f"❌ Error in geographic analysis: {e}")
            return {}
            
    def generate_insights(self, df: pd.DataFrame, quality_metrics: Dict):
        """Generate analytical insights"""
        self.print_subheader("Key Insights")
        
        insights = []
        
        # Data quality insights
        comp_rate = quality_metrics.get("completeness", {}).get("completeness_rate", 0)
        if comp_rate >= 90:
            insights.append("✅ Excellent data completeness (>90%)")
        elif comp_rate >= 70:
            insights.append("⚠️ Good data completeness (70-90%), room for improvement")
        else:
            insights.append("❌ Poor data completeness (<70%), requires attention")
        
        # Consistency insights
        consistency = quality_metrics.get("consistency", {})
        if consistency.get("outliers_count", 0) > 0:
            insights.append(f"🔍 Found {consistency['outliers_count']} potential data outliers")
        
        if consistency.get("extreme_values", 0) > 0:
            insights.append(f"⚠️ Found {consistency['extreme_values']} values >100% (check coverage calculations)")
        
        # Performance insights
        if not df.empty and 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            avg_performance = df['value'].mean()
            
            if avg_performance >= 80:
                insights.append("📈 Strong overall indicator performance (>80%)")
            elif avg_performance >= 60:
                insights.append("📊 Moderate indicator performance (60-80%)")
            else:
                insights.append("📉 Low indicator performance (<60%), needs intervention")
        
        # Trend insights
        indicators_with_trends = self.analysis_results.get("indicators", {})
        improving_count = sum(1 for ind in indicators_with_trends.values() 
                            if "Improving" in str(ind.get("trend", "")))
        declining_count = sum(1 for ind in indicators_with_trends.values() 
                            if "Declining" in str(ind.get("trend", "")))
        
        if improving_count > declining_count:
            insights.append("📈 More indicators showing improvement than decline")
        elif declining_count > improving_count:
            insights.append("📉 More indicators declining than improving - needs attention")
        
        self.analysis_results["insights"] = insights
        
        # Print insights
        for insight in insights:
            print(f"   {insight}")
        
        return insights
        
    def save_analysis_results(self, df: pd.DataFrame):
        """Save analysis results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main results JSON
        results_file = f"health_analysis_results_{timestamp}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        
        # Save data CSV
        if not df.empty:
            data_file = f"health_data_{timestamp}.csv"
            df.to_csv(data_file, index=False)
            print(f"📊 Health data saved: {data_file}")
        
        print(f"📋 Analysis results saved: {results_file}")
        
        # Generate summary report
        self.generate_summary_report(timestamp)
        
    def generate_summary_report(self, timestamp: str):
        """Generate markdown summary report"""
        report_content = f"""# Health Data Analysis Report

**Generated:** {self.analysis_results['analysis_timestamp']}
**DHIS2 Server:** {self.config.base_url}

## 📊 Summary

### Indicators Analyzed
"""
        
        for indicator_name, stats in self.analysis_results.get("indicators", {}).items():
            report_content += f"""
- **{indicator_name}**
  - Average: {stats.get('mean', 0):.1f}%
  - Range: {stats.get('min', 0):.1f}% - {stats.get('max', 0):.1f}%
  - Trend: {stats.get('trend', 'Unknown')}
"""
        
        report_content += f"""
### Data Quality Metrics

- **Completeness:** {self.analysis_results.get('quality_metrics', {}).get('completeness', {}).get('completeness_rate', 0):.1f}%
- **Outliers:** {self.analysis_results.get('quality_metrics', {}).get('consistency', {}).get('outliers_count', 0)}
- **Data Recency:** {self.analysis_results.get('quality_metrics', {}).get('timeliness', {}).get('data_recency', 'Unknown')}

### Key Insights
"""
        
        for insight in self.analysis_results.get("insights", []):
            report_content += f"- {insight}\n"
        
        report_content += f"""
### Recommendations

1. **Data Quality:** Focus on improving data completeness where below 90%
2. **Monitoring:** Investigate any outliers or extreme values
3. **Trends:** Monitor declining indicators for intervention opportunities
4. **Geographic:** Ensure consistent data collection across all organization units

---
*Report generated by pydhis2 Health Data Analysis Demo*
"""
        
        report_file = f"health_analysis_report_{timestamp}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"📄 Summary report saved: {report_file}")
        
    async def run_analysis(self):
        """Run complete health data analysis"""
        self.print_header("🏥 pydhis2 Real Health Data Analysis Demo")
        
        try:
            async with AsyncDHIS2Client(self.config) as client:
                # 1. Get health indicators
                print("🔍 Identifying health indicators...")
                indicators = await self.get_health_indicators(client)
                
                if not indicators:
                    print("❌ No health indicators found. Using default set.")
                    return
                
                # 2. Analyze indicator performance
                df = await self.analyze_indicator_performance(client, indicators)
                
                # 3. Assess data quality
                quality_metrics = await self.assess_data_quality(df)
                
                # 4. Geographic analysis
                geo_analysis = await self.geographic_analysis(client, indicators)
                
                # 5. Generate insights
                insights = self.generate_insights(df, quality_metrics)
                
                # 6. Save results
                self.print_subheader("Saving Results")
                self.save_analysis_results(df)
                
                self.print_header("✅ Health Data Analysis Complete!")
                print(f"📊 Analyzed {len(indicators)} health indicators")
                print(f"🔍 Generated {len(insights)} key insights")
                print(f"📋 Data quality score: {quality_metrics.get('completeness', {}).get('completeness_rate', 0):.1f}%")
                
        except Exception as e:
            print(f"Analysis failed: {e}")


async def main():
    """Main function"""
    # Configuration for DHIS2 demo server
    config = DHIS2Config(
        base_url="https://play.dhis2.org",
        auth=("admin", "district")
    )
    
    analyzer = HealthDataAnalyzer(config)
    await analyzer.run_analysis()


if __name__ == "__main__":
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
