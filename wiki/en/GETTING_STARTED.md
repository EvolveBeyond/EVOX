# Getting Started with RssBot Platform

This comprehensive guide will help you set up and run the revolutionary **RssBot Hybrid Microservices Platform** for development or production use.

## 🎯 Overview

RssBot Platform is the **world's most advanced self-healing, per-service hybrid microservices platform** for Telegram-RSS bots, featuring:

- **🏗️ Per-Service Architecture**: Each service independently chooses `router`/`rest`/`hybrid`/`disabled`
- **⚡ Redis-Cached Registry**: Sub-millisecond service discovery with automatic fallback
- **🤖 AI-Powered Processing**: OpenAI integration for intelligent content summarization
- **🔧 Zero-Downtime Configuration**: Live service reconfiguration without restarts
- **🏥 Self-Healing**: Automatic health monitoring and intelligent routing

## 📋 Prerequisites

### 🔧 Required Software

- **Python 3.11+** - Modern Python with full type hint support
- **Redis 5.0+** - For high-performance caching and job processing
- **PostgreSQL 13+** (recommended) or SQLite for development
- **Git** - For version control

### 🌐 External Services (Optional)

- **Telegram Bot Token** - Get from [@BotFather](https://t.me/botfather) for bot functionality
- **OpenAI API Key** - For AI-powered content processing (optional)
- **Stripe Account** - For payment processing features (optional)

## 🚀 Installation Methods

### Method 1: Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/rssbot-platform.git
cd rssbot-platform

# Install dependencies using rye (modern Python package manager)
pip install rye
rye sync

# Or use pip directly
pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section)
```

### Method 2: Docker Development

```bash
# Clone and start with Docker
git clone https://github.com/your-username/rssbot-platform.git
cd rssbot-platform

# Start all services with docker-compose
docker-compose -f infra/docker-compose.yml up -d

# Check logs
docker-compose logs -f controller_svc
```

### Method 3: Production Installation

```bash
# Install from PyPI (when published)
pip install rssbot-platform

# Or install from source for latest features
pip install git+https://github.com/your-username/rssbot-platform.git
```

## ⚙️ Configuration

### 🔧 Environment Setup

Create and edit `.env` file with your configuration:

```bash
# === Core Platform Configuration ===
DATABASE_URL=postgresql://user:password@localhost:5432/rssbot
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development

# === Service Communication ===
SERVICE_TOKEN=dev_service_token_change_in_production
CONTROLLER_SERVICE_PORT=8004

# === NEW: Per-Service Architecture ===
# Note: LOCAL_ROUTER_MODE is legacy - services now decide independently
LOCAL_ROUTER_MODE=false  # Only used during migration

# === External Services ===
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=sk-your_openai_key_here
STRIPE_SECRET_KEY=sk-your_stripe_key_here

# === Database Settings ===
DB_ECHO=false
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# === Redis Settings (High Performance) ===
REDIS_DECODE_RESPONSES=true
REDIS_HEALTH_CHECK_INTERVAL=30
```

### 🗄️ Database Setup

#### Option 1: PostgreSQL (Production Recommended)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql  # macOS

# Create database and user
sudo -u postgres psql
CREATE DATABASE rssbot;
CREATE USER rssbot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE rssbot TO rssbot_user;
\q

# Update .env
DATABASE_URL=postgresql://rssbot_user:your_secure_password@localhost:5432/rssbot
```

#### Option 2: SQLite (Development Only)

```bash
# Update .env for SQLite (simpler for development)
DATABASE_URL=sqlite:///./rssbot.db
```

### 🔴 Redis Setup (Required for Performance)

```bash
# Install Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis  # macOS

# Start Redis
sudo systemctl start redis  # Ubuntu/Debian
brew services start redis  # macOS

# Verify Redis is running
redis-cli ping
# Should return: PONG

# Configure Redis for production (optional)
sudo nano /etc/redis/redis.conf
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru
```

## 🚀 Running the Platform

### 🎯 New Architecture: Multiple Entry Points

The new platform offers **three ways** to start, providing maximum flexibility:

#### Method 1: Core Platform (Recommended)

```bash
# Start the complete platform using the core entry point
python -m rssbot

# Platform automatically:
# 1. Initializes Redis-backed service registry
# 2. Discovers all services
# 3. Mounts router-enabled services
# 4. Starts health monitoring
# 5. Applies per-service connection decisions
```

#### Method 2: Controller Service Wrapper

```bash
# Start using the simplified controller wrapper
python services/controller_svc/main.py

# This wrapper uses the core platform internally
```

#### Method 3: Direct Uvicorn

```bash
# Start directly with uvicorn for custom configuration
uvicorn rssbot.core.controller:create_platform_app \
    --host 0.0.0.0 \
    --port 8004 \
    --reload
```

### 🔧 Service Configuration (NEW!)

The revolutionary **per-service architecture** allows each service to independently choose its connection method:

```bash
# Configure individual services after startup
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "router"}'

# Available connection methods:
# "router"   - In-process FastAPI router (fastest)
# "rest"     - HTTP calls with JSON (scalable) 
# "hybrid"   - Router preferred, auto-fallback to REST
# "disabled" - Completely disabled

# Bulk configuration for multiple services
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "ai_svc": "router",
       "formatting_svc": "router", 
       "bot_svc": "rest",
       "payment_svc": "rest"
     }'
```

### 🔄 Migration from Legacy Architecture

If upgrading from the old global `LOCAL_ROUTER_MODE` system:

```bash
# Automatic migration (preserves your configuration preferences)
curl -X POST http://localhost:8004/admin/migrate-from-global-mode \
     -H "X-Service-Token: dev_service_token_change_in_production"

# The system automatically converts:
# LOCAL_ROUTER_MODE=true  + has router  → connection_method="router"
# LOCAL_ROUTER_MODE=false + any service → connection_method="rest"
```

## ✅ Verification & Health Monitoring

### 🩺 Platform Health Checks

```bash
# Check platform health (new architecture)
curl http://localhost:8004/health

# Expected response:
{
  "status": "healthy",
  "platform": "rssbot_hybrid_microservices",
  "architecture": "per_service_core_controller",  # NEW!
  "version": "2.0.0",
  "cache_stats": {"cache_available": true},
  "mounted_services": 4
}
```

### 📊 Service Management

```bash
# View all services with their connection methods
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/services

# Response includes per-service information:
{
  "services": [
    {
      "name": "ai_svc",
      "connection_method": "router",
      "health_status": "healthy",
      "is_mounted": true,
      "has_router": true
    }
  ],
  "total_services": 8,
  "mounted_count": 4
}

# Get specific service configuration
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/services/ai_svc/connection-method
```

### ⚡ Performance Monitoring

```bash
# Monitor cache performance (NEW!)
curl -H "X-Service-Token: dev_service_token_change_in_production" \
     http://localhost:8004/admin/cache/stats

# Response shows Redis performance:
{
  "cache_available": true,
  "redis_info": {
    "keyspace_hits": 1000,
    "keyspace_misses": 10,
    "used_memory_human": "2.5M"
  },
  "service_cache_keys": 12
}
```

### 📚 API Documentation

Access interactive API documentation:

- **🎯 Platform Controller**: http://localhost:8004/docs
- **🗄️ Services Overview**: http://localhost:8004/services
- **🔧 Admin APIs**: http://localhost:8004/admin/

For router-mounted services, APIs are available at:
- `/ai/*` - AI service endpoints  
- `/formatting/*` - Content formatting
- `/user/*` - User management
- `/db/*` - Database operations

## 🧪 Basic Usage Examples

### 🤖 Test AI Features

```bash
# AI-powered content summarization
curl -X POST http://localhost:8004/ai/summarize \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "text": "Long article content here...",
       "max_length": 100,
       "style": "technical"
     }'

# Response: {"summary": "Intelligent summary...", "confidence": 0.95}
```

### 📝 Test Content Formatting

```bash
# Format content for Telegram with templates
curl -X POST http://localhost:8004/formatting/format \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "content": "Raw RSS content",
       "format": "telegram_html",
       "template": "news_article",
       "channel_profile": {"style": "professional"}
     }'
```

### 📡 Test RSS Processing Workflow

```bash
# Complete RSS-to-Telegram workflow
curl -X POST http://localhost:8004/feeds/process \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "feed_url": "https://feeds.feedburner.com/techcrunch",
       "channel_id": "@your_channel",
       "enable_ai_summary": true,
       "template": "tech_news"
     }'
```

## 🔧 Advanced Configuration

### 🎯 Service-Specific Settings

```bash
# Configure service for maximum performance (router mode)
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "router"}'

# Configure service for isolation (REST mode)
curl -X POST http://localhost:8004/services/payment_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "rest"}'

# Configure service for reliability (hybrid mode)
curl -X POST http://localhost:8004/services/bot_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{"connection_method": "hybrid"}'
```

### 🔄 Live Configuration Changes

```bash
# The platform supports zero-downtime configuration:

# 1. Change service method
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -d '{"connection_method": "rest"}'

# 2. Service automatically switches to new method
# 3. No restart required!

# 4. Verify change
curl http://localhost:8004/services/ai_svc/connection-method
```

## 🚨 Troubleshooting

### 🔧 Common Issues

#### ❌ "Registry not initialized" errors

**Problem**: Service registry failed to start

**Solutions**:
```bash
# Check Redis connection
redis-cli ping

# Check platform logs
python -m rssbot 2>&1 | grep -E "(ERROR|WARN)"

# Restart with debug logging
LOGLEVEL=DEBUG python -m rssbot
```

#### ❌ Service connection method errors

**Problem**: Can't set service connection method

**Solutions**:
```bash
# Check service exists in registry
curl -H "X-Service-Token: $TOKEN" http://localhost:8004/services

# Check valid connection methods
# Valid: "router", "rest", "hybrid", "disabled"

# Reset to default
curl -X DELETE -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache
```

#### ❌ Cache performance issues

**Problem**: Slow service decisions

**Solutions**:
```bash
# Check Redis performance
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache/stats

# Clear and rebuild cache
curl -X DELETE -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache

# Check Redis memory usage
redis-cli info memory
```

### 🔍 Performance Optimization

#### ⚡ Maximum Speed Configuration

```bash
# Set high-performance services to router mode
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "ai_svc": "router",
       "formatting_svc": "router",
       "user_svc": "router"
     }'
```

#### 🏭 Production Scalability

```bash
# Set services for independent scaling
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: dev_service_token_change_in_production" \
     -d '{
       "bot_svc": "rest",
       "payment_svc": "rest",
       "channel_mgr_svc": "rest"
     }'
```

## 📈 Performance Monitoring

### 📊 Built-in Metrics

```bash
# Platform performance overview
curl http://localhost:8004/health

# Detailed cache statistics
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache/stats

# Service-specific performance
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/services
```

### ⚡ Expected Performance

- **Service Decision Lookup**: < 1ms (Redis cache)
- **Router Service Calls**: < 5ms (in-process)  
- **REST Service Calls**: < 50ms (HTTP)
- **Health Check Cycle**: 60 seconds
- **Cache TTL**: 5 minutes (configurable)

## 🎯 Next Steps

### 🚀 Development Workflow

```bash
# Start development environment
python -m rssbot

# Configure for fast development (router mode)
curl -X POST http://localhost:8004/admin/bulk-connection-methods \
     -d '{"ai_svc": "router", "formatting_svc": "router"}'

# Make changes to services...
# No restart required! Changes apply automatically
```

### 📚 Further Reading

1. **[🏗️ Architecture Guide](ARCHITECTURE.md)**: Deep dive into the platform design
2. **[👨‍💻 Development Guide](DEVELOPMENT.md)**: Adding features and services  
3. **[🚀 Production Guide](PRODUCTION.md)**: Deployment and scaling
4. **[📡 API Reference](API.md)**: Complete API documentation

### 🤝 Getting Help

- **📖 Documentation**: Comprehensive guides in `docs/` directory
- **🐛 Issues**: [GitHub Issues](https://github.com/your-username/rssbot-platform/issues) for bugs
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-username/rssbot-platform/discussions) for questions
- **📧 Support**: maintainers@rssbot-platform.com

## 🎉 Success!

You now have the **world's most advanced hybrid microservices platform** running! 

**Key capabilities unlocked:**
- ⚡ **Sub-millisecond service decisions** via Redis cache
- 🔧 **Live configuration changes** without restarts
- 🏥 **Self-healing architecture** with automatic failover
- 🎯 **Per-service optimization** for performance or scalability
- 🚀 **Enterprise-grade reliability** with comprehensive monitoring

**Happy building!** 🚀✨