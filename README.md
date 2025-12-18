# Evox - Modern Python Microservices Framework (v0.0.5-alpha)

Evox is a modern microservices framework for Python that makes building scalable backend services simple and intelligent.

## 🚀 Quick Start

### Installation

```bash
# Using Rye (recommended)
rye add evox

# Or using pip
pip install evox
```

### Create Your First Service

```bash
# Create a new project
evox new pj my_project
cd my_project

# Create a service
evox new sv user_service

# Run in development mode
evox run --dev
```

## 🔄 Dual Syntax Support

Evox supports two ways to build services:

### Function-Based Syntax (Simple & Familiar)

```python
from evox import service, get, post, delete, Param, Body

# Create service
svc = service("user-service").port(8000).build()

# Define endpoints
@get("/users/{user_id:int}")
async def get_user(user_id: int = Param(int)):
    return {"id": user_id, "name": f"User {user_id}"}

@post("/users")
async def create_user(user_data: dict = Body(dict)):
    return {"status": "created", "user": user_data}

@delete("/users/{user_id:int}")
async def delete_user(user_id: int = Param(int)):
    return {"status": "deleted", "user_id": user_id}

if __name__ == "__main__":
    svc.run(dev=True)
```

### Class-Based Syntax (Organized & Scalable)

```python
from evox import service, Controller, GET, POST, DELETE, Param, Body

# Create service
svc = service("user-service").port(8000).build()

@Controller("/users")
class UserController:
    @GET("/{user_id:int}")
    async def get_user(self, user_id: int = Param(int)):
        return {"id": user_id, "name": f"User {user_id}"}
    
    @POST("/")
    async def create_user(self, user_data: dict = Body(dict)):
        return {"status": "created", "user": user_data}
    
    @DELETE("/{user_id:int}")
    async def delete_user(self, user_id: int = Param(int)):
        return {"status": "deleted", "user_id": user_id}

if __name__ == "__main__":
    svc.run(dev=True)
```

## 💉 Type-Safe Lazy Dependency Injection

Evox provides clean, lazy dependency injection with full type safety:

```python
from evox import service, get, inject
from evox.core.inject import inject_dependency
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str
    port: int

# Type-safe injection
db_config = inject(DatabaseConfig)  # Lazy - only loads when accessed
user_db = inject('db')             # String-based injection
auth_svc = inject.service('auth')  # Service proxy injection

@get("/users")
async def get_users():
    # Dependencies are resolved automatically
    config = db_config  # Lazy loading happens here
    users = await user_db.get_all_users()
    return {"users": users}
```

## 🧠 Environmental Intelligence

Evox understands your application context automatically:

### Automatic Data Understanding

```python
from evox import service, post, Body
from pydantic import BaseModel

class CriticalRequest(BaseModel):
    data: str
    priority: str = "high"  # Automatically gets high priority

svc = service("smart-service").build()

@post("/process")
async def process_data(request: CriticalRequest = Body(CriticalRequest)):
    # Framework automatically prioritizes based on schema
    return {"processed": True}
```

### Context-Aware Processing

```python
from evox import service, get, Query
from evox.core.intelligence import understand_requester_context

svc = service("adaptive-service").build()

@get("/data")
async def get_data(user_type: str = Query(str, "regular")):
    # Framework adapts based on requester context
    headers = {"X-Requester-Type": user_type}
    context = understand_requester_context(headers, {})
    
    if context["priority"] == "high":
        # Fast processing for important users
        return {"data": "premium_content"}
    else:
        # Standard processing for regular users
        return {"data": "standard_content"}
```

### Resource-Aware Concurrency

```python
from evox.core.intelligence import auto_adjust_concurrency

# Automatically adjust based on system load
auto_adjust_concurrency()
```

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

## 🛠️ CLI Commands

```bash
# Project management
evox new pj my_project    # Create new project
evox new sv my_service    # Create new service

# Development
evox run --dev           # Run in development mode
evox test                # Run tests

# Monitoring
evox health              # Generate health report
evox status              # Show platform status
```

## 🔧 Key Features

### 🎯 Data-Intent-Aware Architecture
- System infers storage/cache/consistency behavior from explicit data intents
- No mandatory DB/ORM/Redis - defaults to in-memory (ephemeral, TTL-aware)
- Unified `data_io` API: `data_io.read(intent, key)` and `data_io.write(intent, obj/data)`

### 🔐 Robust Authentication
- JWT + Role-Based Access Control
- Automatic detection of internal vs external calls
- Intent-integrated security

### ⚡ Priority-Aware Concurrency
- Strict priority enforcement (HIGH > MEDIUM > LOW)
- Concurrency caps prevent resource exhaustion
- Fair scheduling within same priority levels

### 🧼 Clean & Minimal
- Zero external dependencies by default
- SQLite optional lightweight fallback
- ORM completely optional
- Heavy consistency/cache handled transparently

## 📚 Examples

Check out the examples in `evox/examples/`:
- `template_example.py` - Basic service patterns
- `dual_syntax_showcase.py` - Both syntax approaches
- `intelligence_template.py` - Environmental intelligence features

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📄 License

Apache 2.0 License - See LICENSE file for details.