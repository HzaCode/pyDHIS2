#!/usr/bin/env python3
"""
{{ cookiecutter.project_name }} - Pipeline Runner Script

Usage examples:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --config configs/custom.yml
"""

import asyncio
import os
import sys
from pathlib import Path
import argparse
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import pydhis2
try:
    from pydhis2.core.types import DHIS2Config, AnalyticsQuery
    from pydhis2.core.client import AsyncDHIS2Client
    from pydhis2.dqr.metrics import CompletenessMetrics, ConsistencyMetrics, TimelinessMetrics
except ImportError as e:
    print(f"Error: Failed to import pydhis2 module: {e}")
    print("Please ensure pydhis2 is installed: pip install pydhis2")
    sys.exit(1)

# Import other dependencies
import pandas as pd
import yaml
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "configs/dhis2.yml") -> dict:
    """Load configuration file"""
    config_file = project_root / config_path
    
    if not config_file.exists():
        logger.warning(f"Configuration file not found: {config_file}")
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


async def fetch_analytics_data(client: AsyncDHIS2Client, config: dict) -> pd.DataFrame:
    """Fetch Analytics data"""
    logger.info("Fetching Analytics data...")
    
    # Get query parameters from config or environment variables
    dx = config.get('dx', os.getenv('DHIS2_DX', 'your_indicator_id'))
    ou = config.get('ou', os.getenv('DHIS2_OU', 'your_org_unit_id'))
    pe = config.get('pe', os.getenv('DHIS2_PE', '2023Q1:2023Q4'))
    
    query = AnalyticsQuery(dx=dx, ou=ou, pe=pe)
    
    try:
        df = await client.analytics.to_pandas(query)
        logger.info(f"Successfully fetched {len(df)} records")
        return df
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        raise


def run_dqr_analysis(df: pd.DataFrame, config: dict) -> dict:
    """Run data quality review"""
    logger.info("Running data quality review...")
    
    dqr_config = config.get('dqr', {})
    
    # Run various metrics
    completeness_metrics = CompletenessMetrics(dqr_config.get('completeness', {}))
    completeness_results = completeness_metrics.calculate(df)
    
    consistency_metrics = ConsistencyMetrics(dqr_config.get('consistency', {}))
    consistency_results = consistency_metrics.calculate(df)
    
    timeliness_metrics = TimelinessMetrics(dqr_config.get('timeliness', {}))
    timeliness_results = timeliness_metrics.calculate(df)
    
    all_results = completeness_results + consistency_results + timeliness_results
    
    # Calculate overall score
    pass_count = sum(1 for r in all_results if r.status == "pass")
    total_count = len(all_results)
    overall_score = pass_count / total_count if total_count > 0 else 0
    
    logger.info(f"Data quality review finished: {pass_count}/{total_count} metrics passed ({overall_score:.1%})")
    
    return {
        'results': all_results,
        'overall_score': overall_score,
        'pass_count': pass_count,
        'total_count': total_count
    }


def save_results(df: pd.DataFrame, dqr_results: dict, output_dir: Path):
    """Save results"""
    logger.info(f"Saving results to: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save raw data
    data_file = output_dir / "analytics_data.parquet"
    df.to_parquet(data_file, index=False)
    logger.info(f"Data saved: {data_file}")
    
    # Save DQR results
    dqr_summary = {
        'overall_score': dqr_results['overall_score'],
        'pass_count': dqr_results['pass_count'], 
        'total_count': dqr_results['total_count'],
        'metrics': [
            {
                'name': r.metric_name,
                'value': r.value,
                'status': r.status,
                'message': r.message
            }
            for r in dqr_results['results']
        ]
    }
    
    import json
    dqr_file = output_dir / "dqr_summary.json"
    with open(dqr_file, 'w', encoding='utf-8') as f:
        json.dump(dqr_summary, f, indent=2, ensure_ascii=False)
    logger.info(f"DQR results saved: {dqr_file}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description=f"Run {{ cookiecutter.project_name }} data analysis pipeline")
    parser.add_argument('--config', default='configs/dhis2.yml', help='Path to configuration file')
    parser.add_argument('--output', default='data/results', help='Output directory')
    args = parser.parse_args()
    
    # Load environment variables
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        logger.warning("No .env file found, please ensure DHIS2 environment variables are set")
    
    # Load configuration
    config = load_config(args.config)
    
    # Validate required environment variables
    required_vars = ['DHIS2_URL', 'DHIS2_USERNAME', 'DHIS2_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables or create a .env file")
        return 1
    
    # Create DHIS2 client configuration
    client_config = DHIS2Config(
        base_url=os.getenv('DHIS2_URL'),
        auth=(os.getenv('DHIS2_USERNAME'), os.getenv('DHIS2_PASSWORD')),
        rps=config.get('connection', {}).get('rps', 5),
        concurrency=config.get('connection', {}).get('concurrency', 3)
    )
    
    try:
        # Execute pipeline
        async with AsyncDHIS2Client(client_config) as client:
            # 1. Fetch data
            df = await fetch_analytics_data(client, config)
            
            # 2. Data quality review
            dqr_results = run_dqr_analysis(df, config)
            
            # 3. Save results
            output_dir = project_root / args.output
            save_results(df, dqr_results, output_dir)
            
            logger.info("✅ Pipeline executed successfully!")
            logger.info(f"📊 Data records: {len(df):,}")
            logger.info(f"🎯 Quality score: {dqr_results['overall_score']:.1%}")
            
            return 0
            
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
