"""Benchmark utilities for performance testing"""

import time
import asyncio
import statistics
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_name: str
    total_time: float
    success_count: int
    failure_count: int
    response_times: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def median_response_time(self) -> float:
        """Calculate median response time"""
        return statistics.median(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'total_time': self.total_time,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_rate,
            'avg_response_time': self.avg_response_time,
            'median_response_time': self.median_response_time,
            'p95_response_time': self.p95_response_time,
            'min_response_time': min(self.response_times) if self.response_times else 0,
            'max_response_time': max(self.response_times) if self.response_times else 0,
            'total_requests': len(self.response_times),
            'error_count': len(self.error_messages)
        }


class BenchmarkRunner:
    """Run benchmark tests with timing and statistics"""
    
    def __init__(self, name: str = "benchmark"):
        self.name = name
        self.results: List[BenchmarkResult] = []
    
    @asynccontextmanager
    async def time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        start_time = time.perf_counter()
        success_count = 0
        failure_count = 0
        response_times = []
        error_messages = []
        
        class TimingContext:
            def record_success(self, response_time: float):
                nonlocal success_count, response_times
                success_count += 1
                response_times.append(response_time)
            
            def record_failure(self, error_msg: str, response_time: float = 0.0):
                nonlocal failure_count, error_messages, response_times
                failure_count += 1
                error_messages.append(error_msg)
                if response_time > 0:
                    response_times.append(response_time)
        
        context = TimingContext()
        
        try:
            yield context
        finally:
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            result = BenchmarkResult(
                test_name=operation_name,
                total_time=total_time,
                success_count=success_count,
                failure_count=failure_count,
                response_times=response_times,
                error_messages=error_messages
            )
            
            self.results.append(result)
            logger.info(f"Benchmark '{operation_name}' completed: "
                       f"{success_count} success, {failure_count} failures, "
                       f"avg time: {result.avg_response_time:.3f}s")
    
    async def run_repeated_test(
        self,
        test_func: Callable,
        test_name: str,
        repetitions: int = 5,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """Run a test function multiple times and collect statistics"""
        async with self.time_operation(test_name) as timer:
            for i in range(repetitions):
                start = time.perf_counter()
                
                try:
                    await test_func(*args, **kwargs)
                    end = time.perf_counter()
                    timer.record_success(end - start)
                    
                except Exception as e:
                    end = time.perf_counter()
                    timer.record_failure(str(e), end - start)
                    logger.warning(f"Test {test_name} iteration {i+1} failed: {e}")
        
        return self.results[-1]  # Return the most recent result
    
    async def run_concurrent_test(
        self,
        test_func: Callable,
        test_name: str,
        concurrency: int = 5,
        total_requests: int = 50,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """Run concurrent tests to measure performance under load"""
        async with self.time_operation(test_name) as timer:
            semaphore = asyncio.Semaphore(concurrency)
            
            async def single_request():
                async with semaphore:
                    start = time.perf_counter()
                    try:
                        await test_func(*args, **kwargs)
                        end = time.perf_counter()
                        timer.record_success(end - start)
                    except Exception as e:
                        end = time.perf_counter()
                        timer.record_failure(str(e), end - start)
            
            # Create all tasks
            tasks = [single_request() for _ in range(total_requests)]
            
            # Wait for all to complete
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self.results[-1]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all benchmark results"""
        if not self.results:
            return {"message": "No benchmark results available"}
        
        summary = {
            "benchmark_name": self.name,
            "total_tests": len(self.results),
            "results": [result.to_dict() for result in self.results]
        }
        
        # Calculate overall statistics
        all_response_times = []
        total_success = 0
        total_failure = 0
        
        for result in self.results:
            all_response_times.extend(result.response_times)
            total_success += result.success_count
            total_failure += result.failure_count
        
        if all_response_times:
            summary.update({
                "overall_success_rate": total_success / (total_success + total_failure),
                "overall_avg_response_time": statistics.mean(all_response_times),
                "overall_median_response_time": statistics.median(all_response_times),
                "overall_p95_response_time": statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) >= 20 else max(all_response_times)
            })
        
        return summary
    
    def print_summary(self) -> None:
        """Print a formatted summary of results"""
        print(f"\n=== Benchmark Results: {self.name} ===")
        
        for result in self.results:
            print(f"\nTest: {result.test_name}")
            print(f"  Success Rate: {result.success_rate:.1%} ({result.success_count}/{result.success_count + result.failure_count})")
            print(f"  Avg Response Time: {result.avg_response_time:.3f}s")
            print(f"  Median Response Time: {result.median_response_time:.3f}s") 
            print(f"  95th Percentile: {result.p95_response_time:.3f}s")
            print(f"  Total Time: {result.total_time:.3f}s")
            
            if result.error_messages:
                print(f"  Errors: {len(result.error_messages)} unique errors")


class PerformanceProfiler:
    """Simple performance profiler for DHIS2 operations"""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
    
    @asynccontextmanager
    async def profile(self, operation_name: str):
        """Profile an operation"""
        start_time = time.perf_counter()
        
        try:
            yield
            
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            if operation_name not in self.timings:
                self.timings[operation_name] = []
                self.counters[operation_name] = 0
            
            self.timings[operation_name].append(duration)
            self.counters[operation_name] += 1
    
    def get_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for a specific operation"""
        if operation_name not in self.timings:
            return {}
        
        times = self.timings[operation_name]
        
        return {
            'count': len(times),
            'total_time': sum(times),
            'avg_time': statistics.mean(times),
            'median_time': statistics.median(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0.0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations"""
        return {op: self.get_stats(op) for op in self.timings.keys()}
    
    def reset(self) -> None:
        """Reset all collected data"""
        self.timings.clear()
        self.counters.clear()
