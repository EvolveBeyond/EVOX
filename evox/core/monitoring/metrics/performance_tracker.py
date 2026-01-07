"""
Performance Benchmarking Tools for EVOX
Provides comprehensive performance testing and profiling capabilities.
"""

from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import tracemalloc
from contextlib import contextmanager
import functools

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

logger = logging.getLogger(__name__)

class BenchmarkType(Enum):
    """Types of benchmarks"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    CUSTOM = "custom"

@dataclass
class BenchmarkResult:
    """Results from a benchmark test"""
    name: str
    benchmark_type: BenchmarkType
    iterations: int
    duration: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    throughput: float  # requests per second
    memory_usage: Optional[Dict[str, float]] = None
    cpu_usage: Optional[float] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

class PerformanceBenchmark:
    """Comprehensive performance benchmarking system"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self._baseline_memory = None
        self.stats = {
            "benchmarks_run": 0,
            "total_duration": 0.0,
            "peak_memory": 0.0
        }
    
    @contextmanager
    def memory_profiler(self):
        """Context manager for memory profiling"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        snapshot1 = tracemalloc.take_snapshot()
        yield
        snapshot2 = tracemalloc.take_snapshot()
        
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        total_memory = sum(stat.size_diff for stat in top_stats)
        logger.info(f"Memory usage: {total_memory / 1024 / 1024:.2f} MB")
    
    def measure_latency(
        self,
        func: Callable,
        *args,
        iterations: int = 1000,
        warmup: int = 100,
        name: Optional[str] = None,
        **kwargs
    ) -> BenchmarkResult:
        """Measure function latency"""
        name = name or func.__name__
        logger.info(f"Running latency benchmark: {name}")
        
        # Warmup
        for _ in range(warmup):
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
        
        # Measure
        times = []
        start_time = time.perf_counter()
        
        for i in range(iterations):
            iter_start = time.perf_counter()
            
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
            
            iter_end = time.perf_counter()
            times.append(iter_end - iter_start)
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        throughput = iterations / total_duration
        
        # Memory usage
        memory_stats = self._get_memory_stats() if HAS_PSUTIL else None
        
        result = BenchmarkResult(
            name=name,
            benchmark_type=BenchmarkType.LATENCY,
            iterations=iterations,
            duration=total_duration,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev,
            throughput=throughput,
            memory_usage=memory_stats,
            cpu_usage=self._get_cpu_usage() if HAS_PSUTIL else None
        )
        
        self.results.append(result)
        self.stats["benchmarks_run"] += 1
        self.stats["total_duration"] += total_duration
        
        logger.info(f"Latency benchmark completed: {name}")
        logger.info(f"  Avg: {avg_time*1000:.2f}ms, Min: {min_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms")
        logger.info(f"  Throughput: {throughput:.2f} req/s")
        
        return result
    
    async def measure_concurrency(
        self,
        func: Callable,
        concurrency: int = 10,
        duration: Union[float, timedelta] = 30.0,
        name: Optional[str] = None,
        **kwargs
    ) -> BenchmarkResult:
        """Measure concurrent performance"""
        if isinstance(duration, timedelta):
            duration_seconds = duration.total_seconds()
        else:
            duration_seconds = float(duration)
        
        name = name or func.__name__
        logger.info(f"Running concurrency benchmark: {name} ({concurrency} concurrent)")
        
        async def worker(worker_id: int):
            """Worker coroutine"""
            count = 0
            start_time = time.perf_counter()
            
            while time.perf_counter() - start_time < duration_seconds:
                await func(**kwargs)
                count += 1
            
            return count
        
        # Start workers
        start_time = time.perf_counter()
        tasks = [asyncio.create_task(worker(i)) for i in range(concurrency)]
        
        # Wait for completion
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_requests = sum(results)
        total_duration = end_time - start_time
        throughput = total_requests / total_duration
        avg_time = total_duration / total_requests if total_requests > 0 else 0
        
        # Memory and CPU stats
        memory_stats = self._get_memory_stats() if HAS_PSUTIL else None
        
        result = BenchmarkResult(
            name=f"{name}_concurrent",
            benchmark_type=BenchmarkType.CONCURRENCY,
            iterations=total_requests,
            duration=total_duration,
            avg_time=avg_time,
            min_time=0,  # Not measured individually
            max_time=0,  # Not measured individually
            std_dev=0,   # Not measured individually
            throughput=throughput,
            memory_usage=memory_stats,
            cpu_usage=self._get_cpu_usage() if HAS_PSUTIL else None
        )
        
        self.results.append(result)
        self.stats["benchmarks_run"] += 1
        self.stats["total_duration"] += total_duration
        
        logger.info(f"Concurrency benchmark completed: {name}")
        logger.info(f"  Requests: {total_requests}, Duration: {total_duration:.2f}s")
        logger.info(f"  Throughput: {throughput:.2f} req/s, Concurrency: {concurrency}")
        
        return result
    
    def measure_throughput(
        self,
        func: Callable,
        duration: Union[float, timedelta] = 30.0,
        name: Optional[str] = None,
        **kwargs
    ) -> BenchmarkResult:
        """Measure sustained throughput"""
        if isinstance(duration, timedelta):
            duration_seconds = duration.total_seconds()
        else:
            duration_seconds = float(duration)
        
        name = name or func.__name__
        logger.info(f"Running throughput benchmark: {name}")
        
        start_time = time.perf_counter()
        count = 0
        
        while time.perf_counter() - start_time < duration_seconds:
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(**kwargs))
            else:
                func(**kwargs)
            count += 1
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        throughput = count / total_duration
        avg_time = total_duration / count if count > 0 else 0
        
        result = BenchmarkResult(
            name=name,
            benchmark_type=BenchmarkType.THROUGHPUT,
            iterations=count,
            duration=total_duration,
            avg_time=avg_time,
            min_time=0,
            max_time=0,
            std_dev=0,
            throughput=throughput
        )
        
        self.results.append(result)
        return result
    
    def benchmark_with_custom_metric(
        self,
        func: Callable,
        metric_func: Callable[[], Any],
        iterations: int = 100,
        name: Optional[str] = None,
        **kwargs
    ) -> BenchmarkResult:
        """Benchmark with custom metrics"""
        name = name or func.__name__
        logger.info(f"Running custom metric benchmark: {name}")
        
        custom_metrics = {}
        times = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            
            if asyncio.iscoroutinefunction(func):
                asyncio.run(func(**kwargs))
            else:
                func(**kwargs)
            
            end_time = time.perf_counter()
            times.append(end_time - start_time)
            
            # Collect custom metric
            metric_value = metric_func()
            metric_name = metric_func.__name__
            if metric_name not in custom_metrics:
                custom_metrics[metric_name] = []
            custom_metrics[metric_name].append(metric_value)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        throughput = iterations / sum(times)
        
        result = BenchmarkResult(
            name=name,
            benchmark_type=BenchmarkType.CUSTOM,
            iterations=iterations,
            duration=sum(times),
            avg_time=avg_time,
            min_time=min(times),
            max_time=max(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=throughput,
            custom_metrics=custom_metrics
        )
        
        self.results.append(result)
        return result
    
    def _get_memory_stats(self) -> Optional[Dict[str, float]]:
        """Get memory usage statistics"""
        if not HAS_PSUTIL:
            return None
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss": memory_info.rss / 1024 / 1024,  # MB
                "vms": memory_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent()
            }
        except Exception as e:
            logger.warning(f"Could not get memory stats: {e}")
            return None
    
    def _get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage percentage"""
        if not HAS_PSUTIL:
            return None
        
        try:
            process = psutil.Process()
            return process.cpu_percent()
        except Exception as e:
            logger.warning(f"Could not get CPU stats: {e}")
            return None
    
    def get_latest_results(self, limit: int = 10) -> List[BenchmarkResult]:
        """Get latest benchmark results"""
        return self.results[-limit:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary statistics"""
        if not self.results:
            return {}
        
        latencies = [r.avg_time for r in self.results if r.benchmark_type == BenchmarkType.LATENCY]
        throughputs = [r.throughput for r in self.results]
        
        return {
            "total_benchmarks": len(self.results),
            "total_duration": self.stats["total_duration"],
            "avg_latency": statistics.mean(latencies) if latencies else 0,
            "avg_throughput": statistics.mean(throughputs) if throughputs else 0,
            "peak_memory_mb": self.stats["peak_memory"]
        }

# Global benchmark instance
performance_bench = PerformanceBenchmark()

# Convenience decorators
def benchmark_latency(iterations: int = 1000, warmup: int = 100):
    """Decorator to benchmark function latency"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = performance_bench.measure_latency(
                func, *args, iterations=iterations, warmup=warmup, **kwargs
            )
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = performance_bench.measure_latency(
                func, *args, iterations=iterations, warmup=warmup, **kwargs
            )
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def benchmark_throughput(duration: float = 30.0):
    """Decorator to benchmark function throughput"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = performance_bench.measure_throughput(
                func, duration=duration, **kwargs
            )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Additional functions for compatibility
def get_benchmark():
    """Get the global benchmark instance"""
    return performance_bench

async def run_benchmark(func: Callable, *args, benchmark_type: str = "latency", **kwargs):
    """Run a benchmark on a function"""
    if benchmark_type == "latency":
        return performance_bench.measure_latency(func, *args, **kwargs)
    elif benchmark_type == "throughput":
        return performance_bench.measure_throughput(func, *args, **kwargs)
    elif benchmark_type == "concurrency":
        return await performance_bench.measure_concurrency(func, *args, **kwargs)
    else:
        return performance_bench.measure_latency(func, *args, **kwargs)

def generate_benchmark_report():
    """Generate a benchmark report"""
    return performance_bench.get_summary()

async def benchmark_serialization(severity: str = "moderate", duration: int = 30):
    """Run serialization benchmark"""
    import pickle
    test_data = {"data": list(range(1000)), "timestamp": time.time()}
    
    async def serialize_test():
        pickle.dumps(test_data)
    
    async def deserialize_test():
        data = pickle.dumps(test_data)
        pickle.loads(data)
    
    # Run benchmark based on severity
    iterations = {
        "light": 100,
        "moderate": 1000,
        "heavy": 10000
    }.get(severity, 1000)
    
    # Benchmark serialization
    ser_result = performance_bench.measure_latency(
        serialize_test,
        iterations=iterations,
        warmup=10,
        name=f"serialization_{severity}"
    )
    
    # Benchmark deserialization
    deser_result = performance_bench.measure_latency(
        deserialize_test,
        iterations=iterations,
        warmup=10,
        name=f"deserialization_{severity}"
    )
    
    return {
        "serialization": {
            "avg_time_ms": ser_result.avg_time * 1000,
            "throughput": ser_result.throughput,
        },
        "deserialization": {
            "avg_time_ms": deser_result.avg_time * 1000,
            "throughput": deser_result.throughput,
        },
        "iterations": iterations
    }

# Context managers for benchmarking
@contextmanager
def benchmark_block(name: str):
    """Context manager to benchmark a code block"""
    start_time = time.perf_counter()
    yield
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    logger.info(f"Benchmark '{name}': {duration*1000:.2f}ms")

# Export public API
__all__ = [
    "PerformanceBenchmark",
    "BenchmarkResult",
    "BenchmarkType",
    "performance_bench",
    "benchmark_latency",
    "benchmark_throughput",
    "benchmark_block",
    "get_benchmark",
    "run_benchmark",
    "generate_benchmark_report",
    "benchmark_serialization"
]