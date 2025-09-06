"""WHO-DQR core metrics implementation"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass
class MetricResult:
    """Metric result"""
    metric_name: str
    value: float
    status: str  # 'pass', 'warning', 'fail'
    threshold: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


def load_dqr_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load DQR configuration file"""
    if config_path is None:
        # Use default configuration file
        config_path = Path(__file__).parent / "config.yml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        # If loading fails, return an empty config to use defaults
        return {}


class BaseMetrics(ABC):
    """Base class for metrics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # If no config is provided, load the default
        if config is None:
            config = load_dqr_config()
        
        self.config = config or {}
        self.thresholds = self.config.get('thresholds', self._default_thresholds())
    
    @abstractmethod
    def _default_thresholds(self) -> Dict[str, float]:
        """Default thresholds"""
        pass
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> List[MetricResult]:
        """Calculate metrics"""
        pass
    
    def _assess_status(self, value: float, threshold_pass: float, threshold_warn: float) -> str:
        """Assess status"""
        if value >= threshold_pass:
            return 'pass'
        elif value >= threshold_warn:
            return 'warning'
        else:
            return 'fail'


class CompletenessMetrics(BaseMetrics):
    """Completeness metrics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Get completeness-related configuration
        self.completeness_config = self.config.get('completeness', {})
    
    def _default_thresholds(self) -> Dict[str, float]:
        return {
            'reporting_completeness_pass': 0.90,
            'reporting_completeness_warn': 0.80,
            'data_element_completeness_pass': 0.90,
            'data_element_completeness_warn': 0.80,
        }
    
    def calculate(self, data: pd.DataFrame) -> List[MetricResult]:
        """Calculate completeness metrics"""
        results = []
        
        if data.empty:
            return [MetricResult(
                metric_name="completeness_overall",
                value=0.0,
                status="fail",
                message="No data available"
            )]
        
        # 1. Reporting completeness
        if all(col in data.columns for col in ['orgUnit', 'period']):
            reporting_result = self._calculate_reporting_completeness(data)
            results.append(reporting_result)
        
        # 2. Data element completeness
        if 'value' in data.columns:
            element_result = self._calculate_element_completeness(data)
            results.append(element_result)
        
        return results
    
    def _calculate_reporting_completeness(self, data: pd.DataFrame) -> MetricResult:
        """Calculate reporting completeness"""
        # Get thresholds from config, otherwise use defaults
        reporting_config = self.completeness_config.get('reporting', {})
        thresholds_config = reporting_config.get('thresholds', {})
        
        pass_threshold = thresholds_config.get('pass', self.thresholds['reporting_completeness_pass'])
        warn_threshold = thresholds_config.get('warn', self.thresholds['reporting_completeness_warn'])
        
        # Calculate expected organization unit-period combinations
        org_units = data['orgUnit'].unique()
        periods = data['period'].unique()
        expected_combinations = len(org_units) * len(periods)
        
        # Calculate actual reported combinations
        actual_combinations = data[['orgUnit', 'period']].drop_duplicates().shape[0]
        
        completeness = actual_combinations / expected_combinations if expected_combinations > 0 else 0
        
        status = self._assess_status(completeness, pass_threshold, warn_threshold)
        
        return MetricResult(
            metric_name="reporting_completeness",
            value=completeness,
            status=status,
            threshold=pass_threshold,
            message=f"Reporting completeness: {completeness:.1%} ({actual_combinations}/{expected_combinations} org-period combinations)",
            details={
                'expected_combinations': expected_combinations,
                'actual_combinations': actual_combinations,
                'org_units_count': len(org_units),
                'periods_count': len(periods),
                'pass_threshold': pass_threshold,
                'warn_threshold': warn_threshold
            }
        )
    
    def _calculate_element_completeness(self, data: pd.DataFrame) -> MetricResult:
        """Calculate data element completeness"""
        # Get thresholds from config
        indicator_config = self.completeness_config.get('indicator', {})
        nonmissing_config = indicator_config.get('nonmissing', {})
        thresholds_config = nonmissing_config.get('thresholds', {})
        
        pass_threshold = thresholds_config.get('pass', self.thresholds['data_element_completeness_pass'])
        warn_threshold = thresholds_config.get('warn', self.thresholds['data_element_completeness_warn'])
        
        total_values = len(data)
        non_null_values = data['value'].notna().sum()
        
        completeness = non_null_values / total_values if total_values > 0 else 0
        
        status = self._assess_status(completeness, pass_threshold, warn_threshold)
        
        return MetricResult(
            metric_name="data_element_completeness",
            value=completeness,
            status=status,
            threshold=pass_threshold,
            message=f"Data element completeness (non-missing): {completeness:.1%} ({non_null_values}/{total_values} values)",
            details={
                'total_values': total_values,
                'non_null_values': non_null_values,
                'null_values': total_values - non_null_values,
                'pass_threshold': pass_threshold,
                'warn_threshold': warn_threshold
            }
        )


class ConsistencyMetrics(BaseMetrics):
    """Consistency metrics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Get consistency-related configuration
        self.consistency_config = self.config.get('consistency', {})
    
    def _default_thresholds(self) -> Dict[str, float]:
        return {
            'outlier_moderate': 2.0,  # Z-score moderate
            'outlier_extreme': 3.0,   # Z-score extreme
            'trend_consistency_pass': 0.90,
            'trend_consistency_warn': 0.75,
        }
    
    def calculate(self, data: pd.DataFrame) -> List[MetricResult]:
        """Calculate consistency metrics"""
        results = []
        
        if data.empty or 'value' not in data.columns:
            return [MetricResult(
                metric_name="consistency_overall",
                value=0.0,
                status="fail",
                message="Insufficient data for consistency analysis"
            )]
        
        # 1. Outlier detection
        outlier_result = self._detect_outliers(data)
        results.append(outlier_result)
        
        # 2. Time series consistency
        if 'period' in data.columns:
            trend_result = self._assess_trend_consistency(data)
            results.append(trend_result)
        
        return results
    
    def _detect_outliers(self, data: pd.DataFrame) -> MetricResult:
        """Detect outliers"""
        numeric_data = pd.to_numeric(data['value'], errors='coerce').dropna()
        
        if len(numeric_data) < 3:
            return MetricResult(
                metric_name="outlier_detection",
                value=0.0,
                status="warning",
                message="Insufficient data for outlier detection"
            )
        
        # Get outlier thresholds from config
        outliers_config = self.consistency_config.get('outliers', {})
        zscore_config = outliers_config.get('zscore', {})
        extreme_threshold = zscore_config.get('extreme', self.thresholds['outlier_extreme'])
        
        # Calculate Z-scores
        z_scores = np.abs((numeric_data - numeric_data.mean()) / numeric_data.std())
        outliers = z_scores > extreme_threshold
        outlier_count = outliers.sum()
        outlier_rate = outlier_count / len(numeric_data)
        
        # Consistency score = 1 - outlier rate
        consistency_score = 1 - outlier_rate
        
        status = self._assess_status(
            consistency_score,
            0.95,  # >95% consistency is excellent
            0.85   # >85% consistency is good
        )
        
        return MetricResult(
            metric_name="outlier_detection",
            value=consistency_score,
            status=status,
            threshold=0.95,
            message=f"Outlier detection (consistency): {consistency_score:.1%} ({outlier_count} outliers detected)",
            details={
                'total_values': len(numeric_data),
                'outlier_count': outlier_count,
                'outlier_rate': outlier_rate,
                'z_score_threshold': extreme_threshold,
                'max_z_score': z_scores.max() if len(z_scores) > 0 else 0,
            }
        )
    
    def _assess_trend_consistency(self, data: pd.DataFrame) -> MetricResult:
        """Assess trend consistency"""
        if 'period' not in data.columns or 'orgUnit' not in data.columns:
            return MetricResult(
                metric_name="trend_consistency",
                value=0.0,
                status="warning",
                message="Missing required columns for trend analysis"
            )
        
        # Analyze trends by organization unit group
        org_unit_scores = []
        
        for org_unit in data['orgUnit'].unique():
            org_data = data[data['orgUnit'] == org_unit].copy()
            
            if len(org_data) < 3:
                continue
            
            # Sort and calculate coefficient of variation
            org_data = org_data.sort_values('period')
            numeric_values = pd.to_numeric(org_data['value'], errors='coerce').dropna()
            
            if len(numeric_values) >= 3 and numeric_values.std() > 0:
                cv = numeric_values.std() / numeric_values.mean()
                # Consistency score = 1 / (1 + coefficient of variation)
                score = 1 / (1 + cv)
                org_unit_scores.append(score)
        
        if not org_unit_scores:
            return MetricResult(
                metric_name="trend_consistency",
                value=0.0,
                status="warning",
                message="Insufficient data for trend consistency analysis"
            )
        
        overall_score = np.mean(org_unit_scores)
        
        status = self._assess_status(
            overall_score,
            self.thresholds['trend_consistency_pass'],
            self.thresholds['trend_consistency_warn']
        )
        
        return MetricResult(
            metric_name="trend_consistency",
            value=overall_score,
            status=status,
            threshold=self.thresholds['trend_consistency_pass'],
            message=f"Trend consistency: {overall_score:.1%} (based on {len(org_unit_scores)} organizational units)",
            details={
                'org_units_analyzed': len(org_unit_scores),
                'scores': org_unit_scores,
                'avg_score': overall_score,
                'min_score': min(org_unit_scores),
                'max_score': max(org_unit_scores),
            }
        )


class TimelinessMetrics(BaseMetrics):
    """Timeliness metrics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Get timeliness-related configuration
        self.timeliness_config = self.config.get('timeliness', {})
    
    def _default_thresholds(self) -> Dict[str, float]:
        return {
            'submission_timeliness_pass': 0.90,
            'submission_timeliness_warn': 0.75,
            'max_delay_days': 30,  # Maximum acceptable delay in days
        }
    
    def calculate(self, data: pd.DataFrame) -> List[MetricResult]:
        """Calculate timeliness metrics"""
        results = []
        
        if data.empty:
            return [MetricResult(
                metric_name="timeliness_overall",
                value=0.0,
                status="fail",
                message="No data available for timeliness analysis"
            )]
        
        # Check for time-related columns
        time_columns = ['lastUpdated', 'created', 'submissionDate']
        available_time_cols = [col for col in time_columns if col in data.columns]
        
        if not available_time_cols:
            return [MetricResult(
                metric_name="submission_timeliness",
                value=0.0,
                status="warning",
                message="No time columns available for timeliness analysis"
            )]
        
        # Use the first available time column
        time_col = available_time_cols[0]
        timeliness_result = self._calculate_submission_timeliness(data, time_col)
        results.append(timeliness_result)
        
        return results
    
    def _calculate_submission_timeliness(self, data: pd.DataFrame, time_col: str) -> MetricResult:
        """Calculate submission timeliness"""
        # Get thresholds from config
        thresholds_config = self.timeliness_config.get('thresholds', {})
        pass_threshold = thresholds_config.get('timely_pass', self.thresholds['submission_timeliness_pass'])
        warn_threshold = self.thresholds['submission_timeliness_warn']  # No warn in config, use default
        
        try:
            # Convert time column
            data_with_time = data.copy()
            data_with_time[time_col] = pd.to_datetime(data_with_time[time_col], errors='coerce')
            
            # Filter valid time data
            valid_time_data = data_with_time[data_with_time[time_col].notna()]
            
            if valid_time_data.empty:
                return MetricResult(
                    metric_name="submission_timeliness",
                    value=0.0,
                    status="warning",
                    message="No valid timestamps for timeliness analysis"
                )
            
            # Simplified timeliness calculation: based on data recency
            now = pd.Timestamp.now()
            max_delay = pd.Timedelta(days=self.thresholds['max_delay_days'])
            
            # Calculate proportion of timely submissions
            timely_submissions = valid_time_data[
                (now - valid_time_data[time_col]) <= max_delay
            ]
            
            timeliness_rate = len(timely_submissions) / len(valid_time_data)
            
            status = self._assess_status(timeliness_rate, pass_threshold, warn_threshold)
            
            return MetricResult(
                metric_name="submission_timeliness",
                value=timeliness_rate,
                status=status,
                threshold=pass_threshold,
                message=f"Submission timeliness: {timeliness_rate:.1%} (based on {time_col} column)",
                details={
                    'total_records': len(valid_time_data),
                    'timely_records': len(timely_submissions),
                    'max_delay_days': self.thresholds['max_delay_days'],
                    'time_column_used': time_col,
                    'pass_threshold': pass_threshold,
                    'warn_threshold': warn_threshold
                }
            )
            
        except Exception as e:
            return MetricResult(
                metric_name="submission_timeliness",
                value=0.0,
                status="fail",
                message=f"Error calculating timeliness: {str(e)}"
            )
