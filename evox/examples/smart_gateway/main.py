"""
EVOX Smart Gateway Blue-Print
============================

An intelligence-driven gateway demonstrating:
- SystemMonitor detecting high load and triggering auto_adjust_concurrency()
- Priority Queues handling CRITICAL vs LOW priority requests
- Environmental intelligence for adaptive behavior
- Resource protection mechanisms

This example shows how to build an adaptive system that protects its own resources.
"""

import asyncio
from typing import Dict, Any
from evox import service
from evox.core.intelligence import SystemMonitor
from evox.core.queue import PriorityAwareQueue
from .gateway.intelligence_engine import intelligence_engine
from .services.gateway_service import gateway_service, gateway_svc


class SmartGatewayManager:
    """
    Smart Gateway Manager
    
    This class manages the intelligent gateway system, coordinating between
    the intelligence engine, system monitor, priority queues, and other
    components to create an adaptive, resource-protecting gateway.
    """
    
    def __init__(self):
        self._intelligence_engine = intelligence_engine
        self._system_monitor = SystemMonitor()
        self._priority_queue = PriorityAwareQueue()
        self._initialized = False
        self._running = False
    
    async def initialize(self):
        """Initialize the smart gateway system."""
        if self._initialized:
            return
        
        print("🧠 Initializing Smart Gateway System...")
        
        # Initialize components
        await self._system_monitor.initialize()
        
        # Register with any necessary injection systems
        from evox.core.inject import HealthAwareInject
        HealthAwareInject.register_instance("smart_gateway_manager", self)
        HealthAwareInject.register_instance("intelligence_engine", self._intelligence_engine)
        
        self._initialized = True
        print("✅ Smart Gateway System initialized successfully")
    
    async def start_monitoring(self):
        """Start continuous system monitoring."""
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        print("🔍 Starting continuous system monitoring...")
        
        while self._running:
            try:
                # Get system metrics
                metrics = await self._intelligence_engine.get_system_metrics()
                
                # Analyze environment
                analysis = self._intelligence_engine.analyze_environment(metrics)
                
                # Auto-adjust concurrency if needed
                if analysis["priority_adjustment_needed"]:
                    await self._intelligence_engine.auto_adjust_concurrency()
                
                # Wait before next check
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait longer if there's an error
    
    async def stop_monitoring(self):
        """Stop continuous system monitoring."""
        self._running = False
        print("⏹️  Stopping system monitoring...")
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the smart gateway."""
        if not self._initialized:
            await self.initialize()
        
        intelligence_report = await self._intelligence_engine.get_intelligence_report()
        
        status = {
            "system": "smart-gateway",
            "initialized": self._initialized,
            "monitoring_active": self._running,
            "intelligence_engine": {
                "active": True,
                "last_analysis": intelligence_report
            },
            "system_monitor": {
                "active": True,
                "concurrency_limit": self._intelligence_engine._concurrency_limit
            },
            "priority_queue": {
                "size": self._priority_queue.size(),
                "active": True
            }
        }
        
        return status


# Create the smart gateway manager
gateway_manager = SmartGatewayManager()


async def demonstrate_intelligent_behavior():
    """
    Demonstrate the intelligent behavior of the smart gateway.
    """
    print("🧠 EVOX Smart Gateway - Intelligence-Driven System")
    print("=" * 55)
    
    # Initialize the system
    await gateway_manager.initialize()
    
    print("\n🎯 Intelligence-Driven Features:")
    print("• Environmental awareness with real-time system monitoring")
    print("• Adaptive concurrency adjustment based on load conditions")
    print("• Priority queue handling with intelligent request classification")
    print("• Automatic resource protection during high load scenarios")
    print("• Load shedding for non-critical requests when needed")
    
    print("\n💡 Adaptive Behavior Patterns:")
    print("• Detects high CPU/memory load and adjusts accordingly")
    print("• Classifies requests by importance and urgency")
    print("• Protects critical operations during system stress")
    print("• Dynamically adjusts processing capacity based on available resources")
    
    print("\n📊 System Intelligence Capabilities:")
    report = await gateway_manager._intelligence_engine.get_intelligence_report()
    current_metrics = report["current_metrics"]
    analysis = report["environmental_analysis"]
    
    print(f"  Current CPU: {current_metrics['cpu_percent']}%")
    print(f"  Current Memory: {current_metrics['memory_percent']}%")
    print(f"  Current Load: {current_metrics['load_average']}")
    print(f"  Active Requests: {current_metrics['active_requests']}")
    print(f"  Queue Size: {current_metrics['queue_size']}")
    print(f"  System Load: {analysis['system_load']}")
    print(f"  Resource Pressure: {analysis['resource_pressure']}")
    
    print("\n📋 Intelligence Analysis:")
    print(f"  Recommended Action: {analysis['recommendation']}")
    print(f"  Load Shedding Needed: {analysis['load_shedding_needed']}")
    print(f"  Priority Adjustment Needed: {analysis['priority_adjustment_needed']}")
    
    print("\n🔧 Adaptive Mechanisms:")
    print("• auto_adjust_concurrency() - Dynamically adjusts request handling capacity")
    print("• Priority queues - Handles CRITICAL vs LOW requests appropriately")
    print("• Environmental detection - Monitors system load and resource usage")
    print("• Resource protection - Safeguards system during high load")
    
    print("\n✨ Built with Python 3.13+ Modern Syntax:")
    print("• Union syntax: X | Y instead of Union[X, Y]")
    print("• Enhanced type annotations")
    print("• Modern async/await patterns")
    
    print("\n✅ Smart Gateway ready to run with intelligent monitoring")
    print("   Run gateway with: gateway_svc.run(dev=True)")


async def run_smart_gateway():
    """
    Run the smart gateway with continuous monitoring.
    """
    await gateway_manager.initialize()
    
    # Start monitoring in background
    monitoring_task = asyncio.create_task(gateway_manager.start_monitoring())
    
    try:
        # Run the demonstration
        await demonstrate_intelligent_behavior()
        
        # Keep running for a while to show monitoring in action
        print("\n📈 Monitoring system in real-time (will run for 10 seconds)...")
        await asyncio.sleep(10)
        
    finally:
        # Stop monitoring
        await gateway_manager.stop_monitoring()
        monitoring_task.cancel()


if __name__ == "__main__":
    # Run the smart gateway demonstration
    asyncio.run(run_smart_gateway())