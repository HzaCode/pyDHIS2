"""Pipeline configuration models"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class StepConfig(BaseModel):
    """Pipeline step configuration"""
    
    type: str = Field(..., description="Step type")
    name: str = Field(..., description="Step name")
    depends_on: Optional[List[str]] = Field(None, description="Dependent steps")
    enabled: bool = Field(True, description="Whether the step is enabled")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry_count: int = Field(0, description="Number of retries")
    
    # Step-specific parameters
    params: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    
    # Input/Output
    input: Optional[str] = Field(None, description="Input file or data")
    output: Optional[str] = Field(None, description="Output file")
    
    class Config:
        extra = "allow"  # Allow extra fields


class PipelineConfig(BaseModel):
    """Pipeline configuration"""
    
    # Basic information
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    version: str = Field("1.0.0", description="Version number")
    
    # Global configuration
    rps: float = Field(8.0, description="Requests per second")
    concurrency: int = Field(8, description="Number of concurrent connections")
    timeout: int = Field(300, description="Default timeout in seconds")
    
    # Step configuration
    steps: List[StepConfig] = Field(..., description="Pipeline steps")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Pipeline metadata")
    
    def validate_dependencies(self) -> List[str]:
        """Validate step dependencies"""
        errors = []
        step_names = {step.name for step in self.steps}
        
        for step in self.steps:
            if step.depends_on:
                for dep in step.depends_on:
                    if dep not in step_names:
                        errors.append(f"Step '{step.name}' depends on a non-existent step '{dep}'")
        
        return errors
    
    def get_execution_order(self) -> List[StepConfig]:
        """Get the execution order of steps (topological sort)"""
        # Simplified topological sort implementation
        executed = set()
        ordered_steps = []
        remaining_steps = [step for step in self.steps if step.enabled]
        
        while remaining_steps:
            # Find steps with no unmet dependencies
            ready_steps = []
            for step in remaining_steps:
                if not step.depends_on or all(dep in executed for dep in step.depends_on):
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or unmet dependency
                remaining_names = [step.name for step in remaining_steps]
                raise ValueError(f"Detected circular dependency or unmet dependency: {remaining_names}")
            
            # Add ready steps
            for step in ready_steps:
                ordered_steps.append(step)
                executed.add(step.name)
                remaining_steps.remove(step)
        
        return ordered_steps
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'PipelineConfig':
        """Create configuration from YAML"""
        import yaml
        data = yaml.safe_load(yaml_content)
        return cls(**data)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'PipelineConfig':
        """Create configuration from a file"""
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self) -> str:
        """Convert to YAML format"""
        import yaml
        return yaml.dump(self.dict(), allow_unicode=True, default_flow_style=False)
    
    def save_to_file(self, file_path: str) -> None:
        """Save to a file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_yaml())


class PipelineResult(BaseModel):
    """Pipeline execution result"""
    
    pipeline_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, cancelled
    
    # Step results
    step_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Error messages
    errors: List[str] = Field(default_factory=list)
    
    # Statistics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """Execution duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Success rate"""
        if self.total_steps == 0:
            return 0.0
        return self.completed_steps / self.total_steps
    
    def add_step_result(
        self,
        step_name: str,
        status: str,
        start_time: datetime,
        end_time: datetime,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Add a step result"""
        duration = (end_time - start_time).total_seconds()
        
        self.step_results[step_name] = {
            'status': status,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': duration,
            'output_data': output_data or {},
            'error': error
        }
        
        # Update statistics
        if status == 'completed':
            self.completed_steps += 1
        elif status == 'failed':
            self.failed_steps += 1
            if error:
                self.errors.append(f"Step '{step_name}': {error}")
        elif status == 'skipped':
            self.skipped_steps += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary"""
        return {
            'pipeline_name': self.pipeline_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'duration': self.duration,
            'success_rate': self.success_rate,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'skipped_steps': self.skipped_steps,
            'step_results': self.step_results,
            'errors': self.errors
        }
