"""
EVOX Comprehensive Feature Showcase
===================================

This example demonstrates ALL major EVOX capabilities in one place:
- Service building with advanced configuration
- Intent system (both data and operation intents)
- Dependency injection
- Messaging and events
- Background tasks and scheduling
- Caching
- Model mapping
- Authentication
- Monitoring and benchmarking

This is a kitchen-sink example showing the full power of EVOX.
"""

from evoid import (
    service, get, post, put, delete, Controller, 
    inject, override, reset_overrides,
    message_bus, publish_message, subscribe_to_messages,
    scheduler, run_in_background, schedule_recurring,
    cache_layer, cached, cache_get, cache_set,
    model_mapper, map_api_to_core, map_core_to_api,
    auth, AuthManager, AuthConfig,
    performance_bench, run_benchmark,
    data_io, persistence_gateway,
    BaseProvider, SQLiteStorageProvider
)
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Annotated
from datetime import datetime, timedelta
from evoid.core.data.intents.annotated_intents import Critical, Standard, Ephemeral
import asyncio


# === DATA MODELS WITH INTENTS ===

class UserCreateRequest(BaseModel):
    """User creation request with modern intent annotations"""
    name: Annotated[str, Critical(description="User's full name", strong_consistency=True)]
    email: Annotated[str, Critical(description="Email address", encrypt=True, audit_logging=True)]
    age: Optional[Annotated[int, Ephemeral(description="Age in years", ttl_minutes=30)]] = None


class UserResponse(BaseModel):
    """User response model with modern intent annotations"""
    id: Annotated[int, Standard()]
    name: Annotated[str, Critical()]
    email: Annotated[str, Critical(encrypt=True)]
    age: Optional[Annotated[int, Ephemeral(ttl_minutes=15)]] = None
    created_at: Annotated[datetime, Ephemeral(ttl_minutes=5)]


# === DEPENDENCY INJECTION EXAMPLE ===

@inject
class UserService:
    """Service demonstrating dependency injection"""
    
    def __init__(self, db_provider: BaseProvider = None):
        self.db = db_provider or SQLiteStorageProvider(":memory:")
        self.users = {}
        self.next_id = 1
    
    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        user = UserResponse(
            id=self.next_id,
            name=user_data.name,
            email=user_data.email,
            age=user_data.age,
            created_at=datetime.now()
        )
        self.users[self.next_id] = user
        self.next_id += 1
        
        # Publish event about user creation
        await publish_message("user.created", {
            "user_id": user.id,
            "name": user.name,
            "timestamp": user.created_at.isoformat()
        })
        
        return user
    
    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        return self.users.get(user_id)


# === MESSAGE BUS SUBSCRIBER ===

@subscribe_to_messages("user.created")
async def on_user_created(message: Dict[str, Any]):
    """Handle user creation events"""
    print(f"📧 Event received: New user {message['name']} (ID: {message['user_id']}) created at {message['timestamp']}")


# === BACKGROUND TASKS ===

@scheduler.scheduled_task("*/5 * * * *")  # Every 5 minutes
async def cleanup_expired_sessions():
    """Scheduled cleanup task"""
    print("🧹 Running scheduled cleanup task...")


async def send_welcome_email(user_id: int):
    """Background task to send welcome email"""
    print(f"📧 Sending welcome email to user {user_id}")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"✅ Welcome email sent to user {user_id}")


# === CACHED ENDPOINT ===

@get("/analytics/stats")
@cached(ttl=timedelta(minutes=10), key_prefix="analytics")
async def get_analytics_stats() -> Dict[str, Any]:
    """Cached analytics endpoint"""
    # Expensive computation here
    stats = {
        "total_users": 1250,
        "active_today": 847,
        "avg_session_time": "15m 32s",
        "generated_at": datetime.now().isoformat()
    }
    return stats


# === AUTHENTICATED ENDPOINT ===

@auth.required(scopes=["admin"])
@get("/admin/users")
async def get_all_users(current_user: Dict[str, Any] = auth.current_user()) -> Dict[str, Any]:
    """Admin-only endpoint requiring authentication"""
    service = inject(UserService)
    return {
        "users": [user.model_dump() for user in service.users.values()],
        "count": len(service.users),
        "requested_by": current_user.get("username", "unknown")
    }


# === CONTROLLER-BASED SERVICE ===

@Controller("/api/v1/users", tags=["users"])
class UserController:
    """Class-based controller demonstrating structured approach"""
    
    def __init__(self):
        self.user_service = inject(UserService)
    
    @get("/{user_id:int}")
    async def get_user(self, user_id: int) -> UserResponse:
        """Get user by ID"""
        user = await self.user_service.get_user(user_id)
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    @post("/")
    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        """Create new user"""
        user = await self.user_service.create_user(user_data)
        
        # Run background task
        run_in_background(send_welcome_email, user.id)
        
        return user


# === PERFORMANCE MONITORING ===

@performance_bench.track(endpoint="/api/v1/users/", method="POST")
@post("/benchmark/create-user")
async def benchmark_create_user(user_data: UserCreateRequest) -> Dict[str, Any]:
    """Endpoint with automatic performance benchmarking"""
    service = inject(UserService)
    user = await service.create_user(user_data)
    return {"user": user.model_dump(), "benchmarked": True}


# === MAIN SERVICE CONFIGURATION ===

# Build service with all features enabled
app = (
    service("comprehensive-demo")
    .port(8000)
    .enable_fury_serialization(True)
    .configure_cache(l1_size_mb=100, redis_url=None)  # Memory-only for demo
    .enable_benchmarking(True)
    .with_message_bus()
    .with_task_manager()
    .with_model_mapping()
    .build()
)


if __name__ == "__main__":
    print("🚀 EVOX Comprehensive Feature Showcase")
    print("=" * 45)
    print()
    print("Features Demonstrated:")
    print("✅ Service building & configuration")
    print("✅ RESTful endpoints (functional & class-based)")
    print("✅ Data intents (CRITICAL, SENSITIVE, EPHEMERAL)")
    print("✅ Dependency injection")
    print("✅ Message bus & event handling")
    print("✅ Background tasks & scheduling")
    print("✅ Caching with TTL")
    print("✅ Authentication & authorization")
    print("✅ Performance benchmarking")
    print("✅ Model mapping")
    print()
    print("Endpoints Available:")
    print("  GET    /hello/{name}")
    print("  POST   /echo")
    print("  GET    /analytics/stats (cached)")
    print("  GET    /admin/users (authenticated)")
    print("  GET    /api/v1/users/{user_id}")
    print("  POST   /api/v1/users/")
    print("  POST   /benchmark/create-user")
    print()
    print("To run: python 02_comprehensive_showcase.py")
    
    # Uncomment to run:
    # app.run(dev=True)