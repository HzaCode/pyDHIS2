"""Pipeline executor"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydhis2.core.client import AsyncDHIS2Client
from .config import PipelineConfig, PipelineResult, StepConfig
from .steps import StepRegistry

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Pipeline executor"""
    
    def __init__(
        self,
        client: AsyncDHIS2Client,
        output_dir: Optional[Path] = None
    ):
        self.client = client
        self.output_dir = output_dir or Path("pipeline_output")
        self.context: Dict[str, Any] = {}
    
    async def execute(
        self,
        config: PipelineConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """Execute a pipeline"""
        logger.info(f"Starting pipeline execution: {config.name}")
        
        # Validate configuration
        validation_errors = config.validate_dependencies()
        if validation_errors:
            raise ValueError(f"Pipeline configuration validation failed: {validation_errors}")
        
        # Create execution result
        result = PipelineResult(
            pipeline_name=config.name,
            start_time=datetime.now(),
            total_steps=len([step for step in config.steps if step.enabled])
        )
        
        # Create output directory
        run_timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        run_output_dir = self.output_dir / f"{config.name}_{run_timestamp}"
        run_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up context
        execution_context = {
            'output_dir': run_output_dir,
            'pipeline_config': config,
            'start_time': result.start_time,
            **(context or {})
        }
        
        try:
            # Get execution order
            ordered_steps = config.get_execution_order()
            
            # Execute steps
            for step_config in ordered_steps:
                if not step_config.enabled:
                    result.skipped_steps += 1
                    continue
                
                await self._execute_step(step_config, execution_context, result)
            
            # Mark as completed
            result.status = "completed"
            result.end_time = datetime.now()
            
            logger.info(f"Pipeline execution completed: {config.name}")
            logger.info(f"Total duration: {result.duration:.1f}s")
            logger.info(f"Success rate: {result.success_rate:.1%}")
            
        except Exception as e:
            result.status = "failed"
            result.end_time = datetime.now()
            result.errors.append(f"Pipeline execution failed: {str(e)}")
            logger.error(f"Pipeline execution failed: {e}")
            raise
        
        finally:
            # Save the result
            await self._save_result(result, run_output_dir)
        
        return result
    
    async def _execute_step(
        self,
        step_config: StepConfig,
        context: Dict[str, Any],
        result: PipelineResult
    ) -> None:
        """Execute a single step"""
        step_name = step_config.name
        logger.info(f"Executing step: {step_name} ({step_config.type})")
        
        step_start_time = datetime.now()
        
        try:
            # Create step instance
            step = StepRegistry.create_step(step_config)
            
            # Execute step
            if step_config.timeout:
                step_output = await asyncio.wait_for(
                    step.execute(self.client, context),
                    timeout=step_config.timeout
                )
            else:
                step_output = await step.execute(self.client, context)
            
            step_end_time = datetime.now()
            
            # Record success result
            result.add_step_result(
                step_name=step_name,
                status="completed",
                start_time=step_start_time,
                end_time=step_end_time,
                output_data=step_output
            )
            
            # Update context (step output is available to subsequent steps)
            context[f"step_{step_name}_output"] = step_output
            
            duration = (step_end_time - step_start_time).total_seconds()
            logger.info(f"Step {step_name} completed, duration: {duration:.1f}s")
            
        except asyncio.TimeoutError:
            step_end_time = datetime.now()
            error_msg = f"Step timed out (>{step_config.timeout}s)"
            
            result.add_step_result(
                step_name=step_name,
                status="failed",
                start_time=step_start_time,
                end_time=step_end_time,
                error=error_msg
            )
            
            logger.error(f"Step {step_name} timed out")
            
            # If retry is configured, retry logic can be implemented here
            if step_config.retry_count > 0:
                logger.info(f"Step {step_name} will be retried...")
                # TODO: Implement retry logic
            else:
                raise
            
        except Exception as e:
            step_end_time = datetime.now()
            error_msg = str(e)
            
            result.add_step_result(
                step_name=step_name,
                status="failed",
                start_time=step_start_time,
                end_time=step_end_time,
                error=error_msg
            )
            
            logger.error(f"Step {step_name} failed: {e}")
            raise
    
    async def _save_result(
        self,
        result: PipelineResult,
        output_dir: Path
    ) -> None:
        """Save the execution result"""
        import json
        
        result_file = output_dir / "pipeline_result.json"
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Pipeline result saved to: {result_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save pipeline result: {e}")
    
    def set_context(self, key: str, value: Any) -> None:
        """Set execution context"""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get execution context"""
        return self.context.get(key, default)
