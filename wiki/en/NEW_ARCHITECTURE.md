# 🚀 New Per-Service Hybrid Microservices Architecture

## Overview

The RssBot platform has evolved from a global `LOCAL_ROUTER_MODE` system to a **per-service hybrid architecture** where each service independently decides its connection method. This provides unprecedented flexibility and performance optimization.

## Key Changes

### ❌ Old Architecture (OBSOLETE)
```bash
# Global decision for ALL services
LOCAL_ROUTER_MODE=true   # All services use router
LOCAL_ROUTER_MODE=false  # All services use REST
```

### ✅ New Architecture (RECOMMENDED)
```python
# Per-service independent decisions
ai_svc:         connection_method = "router"    # Fast in-process
formatting_svc: connection_method = "rest"     # HTTP calls
user_svc:       connection_method = "hybrid"   # Router + fallback
payment_svc:    connection_method = "disabled" # Completely off
```

## Connection Methods

Each service can choose from 4 connection methods:

| Method    | Description | Use Case |
|-----------|-------------|----------|
| `router`  | In-process mounting via FastAPI router | Maximum performance, shared memory |
| `rest`    | HTTP calls with JSON | Service isolation, scalability |
| `hybrid`  | Router preferred, auto-fallback to REST | Best of both worlds |
| `disabled`| Service completely disabled | Maintenance, debugging |

## Architecture Components

### 🏗️ Core Components

1. **CachedServiceRegistry** (`src/rssbot/discovery/cached_registry.py`)
   - Redis-backed caching for ultra-fast lookups
   - Database persistence with automatic fallback
   - Per-service health tracking

2. **Enhanced ServiceProxy** (`src/rssbot/discovery/proxy.py`)
   - Intelligent routing based on cached decisions
   - Automatic fallback and error handling
   - Real-time health monitoring

3. **Migration Utilities** (`src/rssbot/utils/migration.py`)
   - Backward compatibility helpers
   - Global-to-per-service migration tools

4. **Updated Controller** (`services/controller_svc/main.py`)
   - Per-service mounting decisions
   - New admin endpoints
   - Cache management APIs

## Quick Start

### 1. Installation & Setup

The new architecture is fully backward compatible:

```bash
# Existing setup works unchanged
rye sync
./scripts/start_dev.sh
```

### 2. Verify New Architecture

```bash
# Check that the new architecture is active
curl http://localhost:8004/health
# Should show: "architecture": "per_service_hybrid"

# View per-service decisions
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/local-services
```

### 3. Manage Service Connection Methods

```bash
# Set AI service to use router mode
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "router"}'

# Set formatting service to use REST mode  
curl -X POST http://localhost:8004/services/formatting_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "rest"}'

# Check a service's current method
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/services/ai_svc/connection-method
```

## Code Migration Guide

### Replace LOCAL_ROUTER_MODE Checks

**Old Way (OBSOLETE):**
```python
import os
from rssbot.core.config import get_config

config = get_config()

if config.local_router_mode:
    # mount as router
else:
    # use REST calls
```

**New Way (RECOMMENDED):**
```python
from rssbot.utils.migration import should_use_router_for_service

if await should_use_router_for_service("ai_svc"):
    # mount as router
else:
    # use REST calls
```

### Using ServiceProxy

**Old Way:**
```python
# Direct REST calls or manual router imports
import httpx
response = await client.post("http://localhost:8005/summarize", ...)
```

**New Way:**
```python
# Automatic routing via ServiceProxy
from rssbot.discovery.proxy import get_ai_service

ai = get_ai_service()
result = await ai.summarize(text="Hello world")
# Automatically uses router OR REST based on service configuration
```

## Admin Interface

### Built-in Admin Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/health` | GET | System health with per-service info |
| `/local-services` | GET | All services with their connection methods |
| `/services/{name}/connection-method` | GET/POST | Get/update service connection method |
| `/admin/bulk-connection-methods` | POST | Update multiple services at once |
| `/admin/migrate-from-global-mode` | POST | Migrate from old LOCAL_ROUTER_MODE |
| `/admin/cache` | DELETE | Clear all service caches |
| `/admin/cache/stats` | GET | Cache performance statistics |

### Bulk Configuration Example

```bash
# Configure multiple services at once
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "ai_svc": "router",
       "formatting_svc": "rest", 
       "user_svc": "hybrid",
       "payment_svc": "disabled"
     }'
```

## Performance Benefits

### Redis Caching Layer

- **Sub-millisecond** service decision lookups
- **Automatic cache invalidation** on configuration changes  
- **Database fallback** for reliability
- **Cache statistics** for monitoring

### Intelligent Routing

- **Zero-copy** router calls for maximum performance
- **Health-based** automatic fallbacks
- **Real-time monitoring** with cache updates
- **Graceful degradation** never crashes the platform

## Migration from Global Mode

### Automatic Migration

For existing deployments, the system automatically migrates:

```bash
# Run migration (idempotent, safe to run multiple times)
curl -X POST http://localhost:8004/admin/migrate-from-global-mode \
     -H "X-Service-Token: dev_service_token_change_in_production"
```

Migration Logic:
- `LOCAL_ROUTER_MODE=true` + service has `router.py` → `connection_method="router"`
- `LOCAL_ROUTER_MODE=true` + service has no router → `connection_method="rest"`
- `LOCAL_ROUTER_MODE=false` → `connection_method="rest"`

### Gradual Migration

You can migrate services gradually:

```python
# Test with one service first
await migrate_service_from_global_mode("ai_svc", has_router=True)

# Then migrate others
services_to_migrate = ["formatting_svc", "user_svc", "bot_svc"]
for service in services_to_migrate:
    await migrate_service_from_global_mode(service, has_router=True)
```

## Testing

### Run Comprehensive Tests

```bash
# Run the test suite
python tmp_rovodev_test_new_architecture.py
```

### Manual Testing

```python
# Test individual components
from rssbot.discovery.cached_registry import get_cached_registry
from rssbot.discovery.proxy import ServiceProxy

# Test cached registry
registry = await get_cached_registry()
should_router = await registry.should_use_router("ai_svc")

# Test service proxy
ai = ServiceProxy("ai_svc") 
health = await ai.health_check()
```

## Production Deployment

### Redis Configuration

Ensure Redis is available for optimal performance:

```bash
# In .env
REDIS_URL=redis://your-redis-server:6379/0
```

### Environment Variables

The old `LOCAL_ROUTER_MODE` is still supported for backward compatibility:

```bash
# Legacy support (optional)
LOCAL_ROUTER_MODE=false  # Used only during initial migration

# Per-service decisions take precedence and are stored in database/cache
```

### Monitoring

Monitor the new architecture:

```bash
# Check cache performance
curl -H "X-Service-Token: $SERVICE_TOKEN" \
     http://localhost:8004/admin/cache/stats

# Monitor service health  
curl -H "X-Service-Token: $SERVICE_TOKEN" \
     http://localhost:8004/local-services
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   ⚠️ Redis unavailable, falling back to database
   ```
   - Solution: Check Redis configuration and connectivity
   - Impact: System works but slower (database lookups)

2. **Service Not Found in Registry**
   ```
   Service ai_svc not found in registry, defaulting to REST
   ```
   - Solution: Run service discovery: `GET /local-services`
   - Check: Service directory exists and has proper structure

3. **Router Import Failed**
   ```
   ❌ ai_svc: failed to mount router - No module named 'ai_svc.router'
   ```
   - Solution: Check router.py exists and exports `router`
   - Fallback: Service automatically uses REST mode

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("rssbot").setLevel(logging.DEBUG)

# Check service decisions
from rssbot.utils.migration import bulk_check_router_services
decisions = await bulk_check_router_services()
print(decisions)
```

## Next Steps

1. **Gradual Rollout**: Start with one service, verify it works, then migrate others
2. **Monitor Performance**: Use cache statistics and health endpoints
3. **Custom Admin Dashboard**: Build your own UI using the provided APIs
4. **Production Optimization**: Configure Redis clustering for high availability

## Summary

This new per-service architecture provides:

✅ **Flexibility**: Each service chooses its optimal connection method  
✅ **Performance**: Redis-cached decisions with sub-ms lookups  
✅ **Reliability**: Automatic fallbacks and health monitoring  
✅ **Backward Compatibility**: Existing deployments continue to work  
✅ **Monitoring**: Built-in admin APIs and cache statistics  
✅ **Zero Downtime**: Services can be reconfigured without restarts  

The old global `LOCAL_ROUTER_MODE` is now **obsolete** – welcome to the future of hybrid microservices! 🚀