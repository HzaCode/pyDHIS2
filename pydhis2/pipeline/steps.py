"""Pipeline step implementations"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List
from datetime import datetime
import pandas as pd
import logging

from pydhis2.core.client import AsyncDHIS2Client
from pydhis2.core.types import AnalyticsQuery
from pydhis2.dqr.metrics import CompletenessMetrics, ConsistencyMetrics, TimelinessMetrics
from .config import StepConfig

logger = logging.getLogger(__name__)


class PipelineStep(ABC):
    """Abstract base class for a pipeline step"""
    
    def __init__(self, config: StepConfig):
        self.config = config
        self.name = config.name
        self.params = config.params
    
    @abstractmethod
    async def execute(
        self,
        client: Optional[AsyncDHIS2Client] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the step"""
        pass
    
    def validate_params(self) -> None:
        """Validate parameters"""
        pass


class AnalyticsStep(PipelineStep):
    """Analytics data pull step"""
    
    def validate_params(self) -> None:
        """Validate parameters"""
        required_params = ['dx', 'ou', 'pe']
        for param in required_params:
            if param not in self.params:
                raise ValueError(f"AnalyticsStep is missing required parameter: {param}")
    
    async def execute(
        self,
        client: Optional[AsyncDHIS2Client] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute Analytics data pull"""
        if not client:
            raise ValueError("AnalyticsStep requires a DHIS2 client")
        
        self.validate_params()
        
        # Build query
        query = AnalyticsQuery(
            dx=self.params['dx'],
            ou=self.params['ou'], 
            pe=self.params['pe'],
            co=self.params.get('co'),
            ao=self.params.get('ao')
        )
        
        # Execute query
        df = await client.analytics.to_pandas(query)
        
        # Save result
        output_file = self.config.output or f"{self.name}_output.parquet"
        if context and 'output_dir' in context:
            from pathlib import Path
            output_path = Path(context['output_dir']) / output_file
        else:
            output_path = output_file
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        format_type = self.params.get('format', 'parquet')
        if format_type == 'parquet':
            df.to_parquet(output_path, index=False)
        elif format_type == 'csv':
            df.to_csv(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {format_type}")
        
        logger.info(f"Analytics data saved to: {output_path} ({len(df)} records)")
        
        return {
            'records_count': len(df),
            'output_file': str(output_path),
            'columns': list(df.columns)
        }


class TrackerStep(PipelineStep):
    """Tracker data pull step"""
    
    async def execute(
        self,
        client: Optional[AsyncDHIS2Client] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute Tracker data pull"""
        if not client:
            raise ValueError("TrackerStep requires a DHIS2 client")
        
        # Execute query
        df = await client.tracker.events_to_pandas(
            program=self.params.get('program'),
            status=self.params.get('status'),
            since=self.params.get('since'),
            paging_size=self.params.get('paging_size', 200)
        )
        
        # Save result
        output_file = self.config.output or f"{self.name}_output.parquet"
        if context and 'output_dir' in context:
            from pathlib import Path
            output_path = Path(context['output_dir']) / output_file
        else:
            output_path = output_file
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        
        logger.info(f"Tracker data saved to: {output_path} ({len(df)} records)")
        
        return {
            'records_count': len(df),
            'output_file': str(output_path),
            'columns': list(df.columns)
        }


class DataValueSetsStep(PipelineStep):
    """DataValueSets data pull step"""
    
    async def execute(
        self,
        client: Optional[AsyncDHIS2Client] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute DataValueSets data pull"""
        if not client:
            raise ValueError("DataValueSetsStep requires a DHIS2 client")
        
        # Execute query
        df = await client.datavaluesets.pull(
            data_set=self.params.get('data_set'),
            org_unit=self.params.get('org_unit'),
            period=self.params.get('period'),
            completed_only=self.params.get('completed_only', False)
        )
        
        # Save result
        output_file = self.config.output or f"{self.name}_output.parquet"
        if context and 'output_dir' in context:
            from pathlib import Path
            output_path = Path(context['output_dir']) / output_file
        else:
            output_path = output_file
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        
        logger.info(f"DataValueSets data saved to: {output_path} ({len(df)} records)")
        
        return {
            'records_count': len(df),
            'output_file': str(output_path),
            'columns': list(df.columns)
        }


class DQRStep(PipelineStep):
    """Data Quality Review step"""
    
    def validate_params(self) -> None:
        """Validate parameters"""
        if 'input' not in self.config.dict():
            raise ValueError("DQRStep is missing input file configuration")
    
    async def execute(
        self,
        client: Optional[AsyncDHIS2Client] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute data quality review"""
        from pathlib import Path
        import json
        
        # Get input file
        input_file = self.config.input
        if context and 'output_dir' in context:
            input_path = Path(context['output_dir']) / input_file
        else:
            input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Read data
        if input_path.suffix == '.parquet':
            df = pd.read_parquet(input_path)
        elif input_path.suffix == '.csv':
            df = pd.read_csv(input_path)
        else:
            raise ValueError(f"Unsupported input file format: {input_path.suffix}")
        
        # Run DQR analysis
        dqr_config = self.params.get('config', {})
        
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
        
        # Prepare result
        result_data = {
            'overall_score': overall_score,
            'pass_count': pass_count,
            'total_count': total_count,
            'metrics': [
                {
                    'name': r.metric_name,
                    'value': r.value,
                    'status': r.status,
                    'message': r.message,
                    'details': r.details
                }
                for r in all_results
            ]
        }
        
        # Save JSON summary
        if self.params.get('json_output'):
            json_file = self.params['json_output']
            if context and 'output_dir' in context:
                json_path = Path(context['output_dir']) / json_file
            else:
                json_path = Path(json_file)
            
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"DQR JSON summary saved to: {json_path}")
        
        # Generate HTML report
        if self.params.get('html_output'):
            html_file = self.params['html_output']
            if context and 'output_dir' in context:
                html_path = Path(context['output_dir']) / html_file
            else:
                html_path = Path(html_file)
            
            html_path.parent.mkdir(parents=True, exist_ok=True)
            self._generate_html_report(all_results, df, str(html_path))
            
            logger.info(f"DQR HTML report saved to: {html_path}")
        
        logger.info(f"DQR analysis completed: {pass_count}/{total_count} metrics passed ({overall_score:.1%})")
        
        return result_data
    
    def _generate_html_report(self, results, data, output_path):
        """Generate HTML report"""
        from jinja2 import Template
        
        # Simplified HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Quality Review Report</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>Data Quality Review Report</h1>
            <p>Generated at: {{ timestamp }}</p>
            <p>Number of data records: {{ data_count }}</p>
            
            <h2>Metrics Overview</h2>
            <table border="1">
                <tr><th>Metric</th><th>Value</th><th>Status</th><th>Description</th></tr>
                {% for metric in metrics %}
                <tr>
                    <td>{{ metric.metric_name }}</td>
                    <td>{{ "%.1f%%" | format(metric.value * 100) }}</td>
                    <td>{{ metric.status }}</td>
                    <td>{{ metric.message }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            metrics=results,
            data_count=len(data),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


class StepRegistry:
    """Step registry"""
    
    _steps: Dict[str, Type[PipelineStep]] = {
        'analytics_pull': AnalyticsStep,
        'tracker_pull': TrackerStep,
        'datavaluesets_pull': DataValueSetsStep,
        'dqr': DQRStep,
    }
    
    @classmethod
    def register(cls, step_type: str, step_class: Type[PipelineStep]) -> None:
        """Register a step type"""
        cls._steps[step_type] = step_class
    
    @classmethod
    def create_step(cls, config: StepConfig) -> PipelineStep:
        """Create a step instance"""
        step_class = cls._steps.get(config.type)
        if not step_class:
            raise ValueError(f"Unknown step type: {config.type}")
        
        return step_class(config)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get available step types"""
        return list(cls._steps.keys())
