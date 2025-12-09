# 📡 API Reference

Complete API documentation for the **RssBot Hybrid Microservices Platform**. This document covers all available endpoints, request/response formats, and usage examples.

## 🎯 API Overview

The RssBot Platform provides multiple API interfaces:

- **🎛️ Core Platform API**: Main orchestration and admin endpoints
- **🔧 Service Management API**: Per-service configuration and monitoring
- **🤖 Service-Specific APIs**: Individual service endpoints (AI, formatting, etc.)
- **📊 Monitoring API**: Health checks, metrics, and performance data

### 🔗 Base URLs

```bash
# Core Platform (all deployments)
https://your-platform.com       # Production
http://localhost:8004          # Development

# Service-Specific (REST mode only)  
http://localhost:8001          # Database Service
http://localhost:8002          # Bot Service
http://localhost:8005          # AI Service
http://localhost:8006          # Formatting Service
```

### 🔒 Authentication

All API endpoints require service token authentication:

```bash
# Required header for all requests
X-Service-Token: your_service_token_here

# Example request
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/health
```

## 🎛️ Core Platform API

### Platform Health & Status

#### GET /health

Get platform health and architecture information.

**Response:**
```json
{
  "status": "healthy",
  "platform": "rssbot_hybrid_microservices", 
  "architecture": "per_service_core_controller",
  "version": "2.0.0",
  "cache_stats": {
    "cache_available": true,
    "redis_info": {
      "keyspace_hits": 1000,
      "keyspace_misses": 10
    }
  },
  "mounted_services": 4,
  "core_location": "src/rssbot/core/controller.py"
}
```

**Example:**
```bash
curl http://localhost:8004/health
```

---

### Service Discovery & Management

#### GET /services

List all registered services with their connection methods and status.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "services": [
    {
      "name": "ai_svc",
      "display_name": "AI Service",
      "connection_method": "router",
      "health_status": "healthy",
      "is_mounted": true,
      "has_router": true,
      "last_health_check": "2024-01-15T10:30:00Z"
    },
    {
      "name": "formatting_svc", 
      "display_name": "Formatting Service",
      "connection_method": "rest",
      "health_status": "healthy",
      "is_mounted": false,
      "has_router": true,
      "last_health_check": "2024-01-15T10:29:45Z"
    }
  ],
  "total_services": 8,
  "mounted_count": 4
}
```

**Example:**
```bash
curl -H "X-Service-Token: your_token" \
     http://localhost:8004/services
```

---

#### GET /services/{service_name}/connection-method

Get connection method configuration for a specific service.

**Parameters:**
- `service_name` (path): Name of the service (e.g., "ai_svc")

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "service": "ai_svc",
  "configured_method": "router",
  "effective_method": "router", 
  "should_use_router": true,
  "health_status": "healthy",
  "has_router": true,
  "is_router_mounted": true
}
```

**Example:**
```bash
curl -H "X-Service-Token: your_token" \
     http://localhost:8004/services/ai_svc/connection-method
```

---

#### POST /services/{service_name}/connection-method

Update connection method for a specific service.

**Parameters:**
- `service_name` (path): Name of the service

**Headers:** 
- `X-Service-Token: required`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "connection_method": "router"
}
```

**Valid connection methods:**
- `"router"` - In-process FastAPI router (fastest)
- `"rest"` - HTTP calls with JSON (scalable)
- `"hybrid"` - Router preferred, auto-fallback to REST
- `"disabled"` - Service completely disabled

**Response:**
```json
{
  "success": true,
  "service": "ai_svc",
  "new_connection_method": "router",
  "message": "Connection method updated. Restart controller to apply router mounting changes."
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{"connection_method": "router"}'
```

---

## 🔧 Admin API

### Bulk Service Management

#### POST /admin/bulk-connection-methods

Update connection methods for multiple services simultaneously.

**Headers:**
- `X-Service-Token: required`  
- `Content-Type: application/json`

**Request Body:**
```json
{
  "ai_svc": "router",
  "formatting_svc": "router",
  "bot_svc": "rest", 
  "payment_svc": "rest",
  "user_svc": "hybrid"
}
```

**Response:**
```json
{
  "success": true,
  "updates": {
    "ai_svc": true,
    "formatting_svc": true,
    "bot_svc": true,
    "payment_svc": true,
    "user_svc": true
  },
  "message": "Bulk update completed. Restart controller to apply router mounting changes."
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{
       "ai_svc": "router",
       "formatting_svc": "router",
       "bot_svc": "rest",
       "payment_svc": "rest"
     }'
```

---

#### POST /admin/migrate-from-global-mode

Migrate from legacy global `LOCAL_ROUTER_MODE` to per-service decisions.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "success": true,
  "migration_plan": {
    "ai_svc": "ROUTER (global=true, has_router=true)",
    "formatting_svc": "ROUTER (global=true, has_router=true)", 
    "bot_svc": "REST (global=true, has_router=false)",
    "payment_svc": "REST (global=false, has_router=true)"
  },
  "message": "Migration completed. Each service now has individual connection method."
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/admin/migrate-from-global-mode \
     -H "X-Service-Token: your_token"
```

---

#### POST /admin/remount-services

Re-discover and remount services based on current configuration.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "success": true,
  "mounted_services": ["ai_svc", "formatting_svc", "user_svc"],
  "message": "Services remounted successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/admin/remount-services \
     -H "X-Service-Token: your_token"
```

---

### Cache Management

#### GET /admin/cache/stats

Get detailed cache performance statistics.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "cache_stats": {
    "cache_available": true,
    "redis_info": {
      "keyspace_hits": 1000,
      "keyspace_misses": 10,
      "used_memory_human": "2.5M"
    },
    "service_cache_keys": 12,
    "sample_keys": [
      "rssbot:service:ai_svc:method",
      "rssbot:service:ai_svc:health"
    ]
  },
  "registry_available": true
}
```

**Example:**
```bash
curl -H "X-Service-Token: your_token" \
     http://localhost:8004/admin/cache/stats
```

---

#### DELETE /admin/cache

Invalidate all service caches to force fresh lookups.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "success": true,
  "message": "All service caches invalidated"
}
```

**Example:**
```bash
curl -X DELETE -H "X-Service-Token: your_token" \
     http://localhost:8004/admin/cache
```

---

## 🤖 Service-Specific APIs

### AI Service API

When AI service is mounted as router (`connection_method: "router"`), endpoints are available at `/ai/*`:

#### POST /ai/summarize

Generate AI-powered content summaries.

**Headers:**
- `X-Service-Token: required`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "text": "Long article content to summarize...",
  "max_length": 100,
  "style": "technical",
  "language": "en"
}
```

**Response:**
```json
{
  "summary": "Intelligent summary of the content...",
  "confidence": 0.95,
  "original_length": 1500,
  "summary_length": 98,
  "processing_time_ms": 245
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/ai/summarize \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{
       "text": "Long article content here...",
       "max_length": 100,
       "style": "technical"
     }'
```

---

#### POST /ai/analyze-sentiment

Analyze content sentiment and emotions.

**Request Body:**
```json
{
  "text": "Content to analyze for sentiment",
  "include_emotions": true
}
```

**Response:**
```json
{
  "sentiment": "positive",
  "confidence": 0.87,
  "emotions": {
    "joy": 0.6,
    "trust": 0.4,
    "anticipation": 0.2
  },
  "analysis_time_ms": 123
}
```

---

### Formatting Service API

#### POST /formatting/format

Format content for different platforms and templates.

**Request Body:**
```json
{
  "content": "Raw RSS content to format",
  "format": "telegram_html",
  "template": "news_article", 
  "channel_profile": {
    "style": "professional",
    "language": "en",
    "include_links": true
  }
}
```

**Response:**
```json
{
  "formatted_content": "<b>Formatted HTML content</b>...",
  "metadata": {
    "original_length": 500,
    "formatted_length": 450,
    "template_used": "news_article",
    "format_type": "telegram_html"
  },
  "processing_time_ms": 45
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/formatting/format \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{
       "content": "Raw RSS content",
       "format": "telegram_html", 
       "template": "news_article"
     }'
```

---

### User Service API

#### GET /user/profile/{user_id}

Get user profile and preferences.

**Parameters:**
- `user_id` (path): Telegram user ID

**Response:**
```json
{
  "user_id": 12345678,
  "username": "johndoe",
  "preferences": {
    "language": "en",
    "timezone": "UTC",
    "notification_settings": {
      "email": true,
      "telegram": true
    }
  },
  "subscription": {
    "plan": "premium",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

---

#### PUT /user/profile/{user_id}

Update user profile and preferences.

**Request Body:**
```json
{
  "preferences": {
    "language": "en",
    "timezone": "America/New_York",
    "notification_settings": {
      "email": false,
      "telegram": true
    }
  }
}
```

---

### Bot Service API

#### POST /bot/send-message

Send message through Telegram bot.

**Request Body:**
```json
{
  "chat_id": "@channel_name",
  "text": "Message to send",
  "parse_mode": "HTML",
  "reply_markup": {
    "inline_keyboard": [
      [{"text": "Read More", "url": "https://example.com"}]
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message_id": 12345,
  "chat_id": "@channel_name",
  "sent_at": "2024-01-15T10:30:00Z"
}
```

---

## 📊 Monitoring & Metrics API

### Platform Metrics

#### GET /metrics

Prometheus-compatible metrics endpoint.

**Response:** (Prometheus format)
```
# HELP rssbot_requests_total Total number of requests
# TYPE rssbot_requests_total counter
rssbot_requests_total{method="GET",endpoint="/health"} 1000

# HELP rssbot_response_time_seconds Response time in seconds
# TYPE rssbot_response_time_seconds histogram
rssbot_response_time_seconds_bucket{le="0.1"} 950
rssbot_response_time_seconds_bucket{le="0.5"} 990
rssbot_response_time_seconds_bucket{le="1.0"} 1000

# HELP rssbot_cache_hits_total Total cache hits
# TYPE rssbot_cache_hits_total counter
rssbot_cache_hits_total 10000

# HELP rssbot_services_healthy Number of healthy services
# TYPE rssbot_services_healthy gauge
rssbot_services_healthy 8
```

---

### Service Health Monitoring

#### GET /health/detailed

Detailed health information for all components.

**Headers:** `X-Service-Token: required`

**Response:**
```json
{
  "platform": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "version": "2.0.0"
  },
  "services": [
    {
      "name": "ai_svc",
      "status": "healthy",
      "connection_method": "router",
      "response_time_ms": 2.5,
      "last_check": "2024-01-15T10:30:00Z"
    }
  ],
  "cache": {
    "status": "healthy", 
    "hit_ratio": 0.95,
    "memory_usage_mb": 256
  },
  "database": {
    "status": "healthy",
    "connection_pool": {
      "active": 5,
      "idle": 15
    }
  }
}
```

---

## 🔧 Error Handling

### Standard Error Responses

All API endpoints return standardized error responses:

```json
{
  "error": {
    "code": "SERVICE_NOT_FOUND", 
    "message": "Service 'invalid_svc' not found in registry",
    "details": {
      "service_name": "invalid_svc",
      "available_services": ["ai_svc", "formatting_svc"]
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_12345"
  }
}
```

### HTTP Status Codes

| Status Code | Description | Usage |
|-------------|-------------|-------|
| 200 | OK | Successful requests |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing service token |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation errors |
| 500 | Internal Server Error | Server-side errors |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `INVALID_SERVICE_TOKEN` | Service token is invalid | Check X-Service-Token header |
| `SERVICE_NOT_FOUND` | Service not registered | Check service name spelling |
| `INVALID_CONNECTION_METHOD` | Invalid connection method | Use: router, rest, hybrid, disabled |
| `CACHE_CONNECTION_ERROR` | Redis cache unavailable | Check Redis connectivity |
| `SERVICE_UNAVAILABLE` | Service temporarily down | Retry request or check service health |

---

## 🚀 Usage Examples

### Complete Service Configuration Workflow

```bash
# 1. Check platform health
curl http://localhost:8004/health

# 2. List all services  
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/services

# 3. Configure high-performance services for router mode
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $TOKEN" \
     -d '{
       "ai_svc": "router",
       "formatting_svc": "router",
       "user_svc": "router"  
     }'

# 4. Configure scalable services for REST mode
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $TOKEN" \
     -d '{
       "bot_svc": "rest",
       "payment_svc": "rest",
       "channel_mgr_svc": "rest"
     }'

# 5. Verify configuration
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/services

# 6. Monitor cache performance
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache/stats
```

### AI-Powered Content Processing Pipeline

```bash
# 1. Summarize content with AI
SUMMARY=$(curl -X POST http://localhost:8004/ai/summarize \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $TOKEN" \
     -d '{
       "text": "Very long article content...",
       "max_length": 150,
       "style": "professional"
     }' | jq -r '.summary')

# 2. Format for Telegram
FORMATTED=$(curl -X POST http://localhost:8004/formatting/format \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $TOKEN" \
     -d "{
       \"content\": \"$SUMMARY\",
       \"format\": \"telegram_html\",
       \"template\": \"news_article\"
     }" | jq -r '.formatted_content')

# 3. Send via bot  
curl -X POST http://localhost:8004/bot/send-message \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: $TOKEN" \
     -d "{
       \"chat_id\": \"@your_channel\",
       \"text\": \"$FORMATTED\",
       \"parse_mode\": \"HTML\"
     }"
```

---

## 📚 Interactive API Documentation

### OpenAPI/Swagger UI

The platform provides interactive API documentation:

- **Development**: http://localhost:8004/docs
- **Alternative UI**: http://localhost:8004/redoc

### API Schema

Download the complete OpenAPI schema:

```bash
# Get OpenAPI JSON schema
curl http://localhost:8004/openapi.json > rssbot-api-schema.json

# Get OpenAPI YAML schema  
curl -H "Accept: application/yaml" \
     http://localhost:8004/openapi.json > rssbot-api-schema.yaml
```

---

**The RssBot Platform API provides enterprise-grade functionality with comprehensive type safety, performance optimization, and monitoring capabilities! 🚀📡**