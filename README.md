# EVOX: The Smart companion for Python 3.13+ Services

EVOX is a next-generation, intent-aware service framework that makes building resilient, scalable backend services simple and intelligent. Built for Python 3.13+ with a focus on multi-layered resilience and automatic adaptation.

## 🚀 Quick Start

### Installation

```bash
# Using Rye (recommended)
rye add evox

# Or using pip
pip install evox

# Install different tiers:
pip install evox[nano]      # Core + In-Memory Cache
pip install evox[mini]      # Nano + CLI + File Storage  
pip install evox[standard]  # Mini + SQLite/Postgres + Basic Auth
pip install evox[full]      # All providers (Redis, Advanced Monitoring, etc.)
```

### Create Your First Service

```bash
# Create a new project
evox new project my_project
cd my_project

# Create a service
evox new service user_service

# Run in development mode
evox maintenance sync
evox maintenance status
```

## 🔄 Nested CLI Commands

EVOX features an intuitive nested command structure:

### Create Commands
```bash
evox new project <name>     # Create a new project
evox new service <name>     # Create a new service
evox new plugin <name>      # Create a new plugin template
evox new db <name>          # Add database configuration
```

### Maintenance Commands
```bash
evox maintenance sync       # Sync dependencies via Rye
evox maintenance health     # Run system-wide health checks
evox maintenance status     # Overview of services, plugins, and system load
```

## 🏗️ Professional Blue-Prints

EVOX provides three ready-to-use blueprints for different project scales:

### 1. Nano Project (`nano_project/`)
Perfect for fast, single-file microservices:
- Zero-boilerplate service creation
- Intent-aware Pydantic models
- Multi-layered caching system
- Health-aware dependency injection

### 2. Enterprise System (`enterprise_system/`)
For multi-service, class-based architecture:
- Professional folder layout (services, providers, shared models)
- BaseProvider pattern implementation
- Service-to-service communication via ServiceRegistry
- Multi-layered cache with Redis -> In-Memory fallback

### 3. Smart Gateway (`smart_gateway/`)
For adaptive, intelligence-aware systems:
- Environmental intelligence with SystemMonitor
- Adaptive concurrency adjustment
- Priority queues for CRITICAL vs LOW requests
- Resource protection mechanisms

## 🔄 Dual Syntax Support

EVOX supports two ways to build services:

### Function-Based Syntax (Simple & Familiar)

```python
from evox import service, get, post, delete, Param, Body
from typing import Dict, Any

# Create service
svc = service("user-service").port(8000).build()

# Define endpoints
@get("/users/{user_id:int}")
async def get_user(user_id: int = Param(int)) -> Dict[str, str | int]:
    return {"id": user_id, "name": f"User {user_id}"}

@post("/users")
async def create_user(user_data: Dict[str, Any] = Body(dict)) -> Dict[str, str]:
    return {"status": "created", "user": user_data}
```

### Class-Based Syntax (Organized & Scalable)

```python
from evox import service, Controller, GET, POST, DELETE, Param, Body
from typing import Dict, Any

# Create service
svc = service("user-service").port(8000).build()

@Controller("/api/v1/users", tags=["users"])
class UserController:
    @GET("/{user_id:int}")
    async def get_user(self, user_id: int = Param(int)) -> Dict[str, str | int]:
        return {"id": user_id, "name": f"User {user_id}"}
    
    @POST("/")
    async def create_user(self, user_data: Dict[str, Any] = Body(dict)) -> Dict[str, str]:
        return {"status": "created", "user": user_data}
```

## 🔧 Type-Safe Architecture

EVOX provides full type safety with modern Python features:

### Type-Safe Dependency Injection

```python
from evox import inject
from evox.core.inject import HealthAwareInject
from typing import Dict, Any

# Type-safe dependency injection with health awareness
class DatabaseService:
    async def get_user(self, user_id: str) -> Dict[str, str]:
        return {"id": user_id, "name": f"User {user_id}"}

@get("/users/{user_id}")
async def get_user(user_id: str = Param(str)) -> Dict[str, str]:
    # Health-aware injection with full IDE support
    db: DatabaseService = inject(DatabaseService)
    return await db.get_user(user_id)

# Alternative syntax with explicit type parameter
# db = HealthAwareInject[DatabaseService]()
```

## 🌍 Environmental Intelligence

EVOX understands your data and context automatically:

### Multi-Layered Resilience
EVOX implements a sophisticated caching system with priority fallback:
- **User-defined cache** (highest priority)
- **In-Memory cache** (fast access)
- **File/DB-based cache** (persistent storage)

### Intent-Aware Architecture
The framework automatically adapts based on your declared intentions:
- Data importance understanding from schema
- Context-aware processing
- Resource-aware concurrency adjustment

## ⚡ Intelligent Priority Management

Requests are automatically prioritized based on multiple factors:

```python
# 1. Static priority (decorator)
@get("/critical", priority="high")
async def critical_endpoint():
    return {"status": "urgent"}

# 2. Dynamic priority (runtime)
result = await proxy.user_svc.get_user(123, priority="high")

# 3. Schema-based priority boosting
@post("/process")
async def process_request(request: HighPrioritySchema = Body(HighPrioritySchema)):
    # Priority automatically boosted based on schema metadata
    return {"processed": True}

# 4. Context-aware priority from headers
# X-Priority: high in request headers
```

## 🏗️ Quick Start from Blue-Prints

Check out the professional blue-prints in `evox/examples/`:
- `nano_project/` - Fast, single-file microservices
- `enterprise_system/` - Multi-service, class-based architecture
- `smart_gateway/` - Intelligence-driven adaptive systems
- `beginner_start.py` - Beginner-friendly introduction

## 🚀 New to EVOX? Start with `examples/beginner_start.py`

If you're new to EVOX, start with our beginner-friendly example that shows the absolute simplest way to get started:

```bash
# Navigate to the beginner example
cd evox/examples/

# Run the beginner example
python beginner_start.py
```

Features:
- 5-line functional service example
- 10-line class-based service example
- No configuration needed
- Direct execution with default fallback values
- Demonstrates EVOX's flexibility from simple to complex

EVOX adapts to your skill level: from simple functions to complex enterprise systems.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 📄 License

Apache 2.0 License - See LICENSE file for details.