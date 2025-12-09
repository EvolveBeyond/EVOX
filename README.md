# 🚀 RssBot Platform

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-5.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

> **The world's most advanced self-healing, per-service hybrid microservices platform for Telegram-RSS bots**

A revolutionary platform that transforms RSS feeds into intelligent Telegram experiences with AI-powered summarization, custom formatting, and enterprise-grade microservices architecture.

## ✨ Key Features

### 🏗️ **Hybrid Microservices Architecture**
- **Per-Service Connection Decisions**: Each service independently chooses router (in-process) or REST (HTTP)
- **Redis-Cached Registry**: Sub-millisecond service discovery with automatic fallback
- **Self-Healing**: Automatic health monitoring and intelligent routing
- **Zero-Downtime Configuration**: Live service reconfiguration without restarts

### 🤖 **Intelligent RSS Processing**
- **AI-Powered Summarization**: OpenAI integration for content processing
- **Smart Formatting**: Template-based content transformation
- **Multi-Channel Support**: Manage multiple Telegram channels
- **Real-time Processing**: Instant RSS feed updates

### 💎 **Enterprise Features**
- **Payment Integration**: Stripe-powered subscription management
- **User Profiles**: Advanced user preference system
- **Mini App Dashboard**: Telegram Web App interface
- **Health Monitoring**: Comprehensive service health tracking
- **Security**: JWT-based authentication and service tokens

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Redis 5.0+** (for caching and jobs)
- **PostgreSQL** (recommended) or SQLite
- **Telegram Bot Token** from [@BotFather](https://t.me/botfather)

### One-Command Installation

```bash
# Clone and setup
git clone https://github.com/your-username/rssbot-platform.git
cd rssbot-platform

# Install dependencies
rye sync  # or pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start the platform
python -m rssbot
# Or: ./scripts/start_dev.sh
```

### Verify Installation

```bash
curl http://localhost:8004/health
# Should return: {"architecture": "per_service_hybrid", "status": "healthy"}
```

## 🏗️ Architecture Overview

### 🎯 **Core Platform** (`src/rssbot/`)

```
src/rssbot/
├── core/controller.py          # Platform orchestration engine
├── discovery/cached_registry.py # Redis-backed service registry
├── models/service_registry.py   # Service configuration models  
├── utils/migration.py          # Legacy migration utilities
└── __main__.py                 # Platform entry point
```

### 🔧 **Microservices** (`services/`)

| Service | Port | Purpose | Connection Method |
|---------|------|---------|-------------------|
| **db_svc** | 8001 | Database operations & schema | `router` (fast) |
| **bot_svc** | 8002 | Telegram gateway & webhooks | `rest` (isolated) |
| **ai_svc** | 8005 | OpenAI integration & summarization | `hybrid` (smart) |
| **formatting_svc** | 8006 | Content templating & transformation | `router` (fast) |
| **user_svc** | 8008 | User profiles & preferences | `router` (fast) |
| **payment_svc** | 8003 | Stripe payment processing | `rest` (secure) |
| **controller_svc** | 8004 | Service orchestration | Core platform |

### 🔄 **Connection Methods**

```python
# Each service can choose independently:
ConnectionMethod.ROUTER   # In-process FastAPI router (fastest)
ConnectionMethod.REST     # HTTP calls with JSON (scalable)  
ConnectionMethod.HYBRID   # Router preferred, auto-fallback to REST
ConnectionMethod.DISABLED # Completely disabled
```

## 🎮 Platform Management

### 📊 **View Service Status**

```bash
# Check all services
curl -H "X-Service-Token: your_token" \
     http://localhost:8004/services

# View cache performance  
curl -H "X-Service-Token: your_token" \
     http://localhost:8004/admin/cache/stats
```

### ⚙️ **Configure Services**

```bash
# Set AI service to router mode (fastest)
curl -X POST http://localhost:8004/services/ai_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{"connection_method": "router"}'

# Set bot service to REST mode (isolated)
curl -X POST http://localhost:8004/services/bot_svc/connection-method \
     -H "Content-Type: application/json" \
     -H "X-Service-Token: your_token" \
     -d '{"connection_method": "rest"}'

# Bulk configuration
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

## 🔧 Development

### 🎯 **Multiple Entry Points**

```bash
# Method 1: Core platform (recommended)
python -m rssbot

# Method 2: Controller service wrapper
python services/controller_svc/main.py

# Method 3: Uvicorn directly
uvicorn rssbot.core.controller:create_platform_app --host 0.0.0.0 --port 8004
```

### 🧩 **Adding New Services**

```python
# 1. Create service directory
mkdir services/my_svc

# 2. Implement main.py
from fastapi import FastAPI
from rssbot.discovery.proxy import ServiceProxy

app = FastAPI(title="My Service")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my_svc"}

# 3. Optional: Create router.py for router mode
from fastapi import APIRouter
router = APIRouter()

# 4. Use ServiceProxy for inter-service calls
ai = ServiceProxy("ai_svc")
result = await ai.summarize(text="Hello world")
```

### 🧪 **Testing**

```bash
# Run tests
pytest tests/

# Smoke tests
./scripts/smoke_test.sh

# Test specific service
curl http://localhost:8001/health  # db_svc
curl http://localhost:8005/health  # ai_svc
```

## 🐳 Production Deployment

### **Docker Deployment**

```bash
# Build and run
docker-compose up -d

# Scale specific services
docker-compose up -d --scale formatting_svc=3

# View logs
docker-compose logs -f controller_svc
```

### **Environment Configuration**

```bash
# Production .env
DATABASE_URL=postgresql://user:pass@db:5432/rssbot
REDIS_URL=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=1234567890:your_real_token
SERVICE_TOKEN=super_secure_production_token
ENVIRONMENT=production

# External services
OPENAI_API_KEY=sk-your_openai_key
STRIPE_SECRET_KEY=sk_live_your_stripe_key
```

### **Health Monitoring**

```bash
# Platform health
curl http://localhost:8004/health

# Service-specific health
curl http://localhost:8004/services

# Cache performance
curl -H "X-Service-Token: $TOKEN" \
     http://localhost:8004/admin/cache/stats
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [🏗️ NEW_ARCHITECTURE.md](NEW_ARCHITECTURE.md) | Complete per-service architecture guide |
| [📖 docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Detailed setup and configuration |
| [🏛️ docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and patterns |
| [📡 docs/API.md](docs/API.md) | Complete API reference |
| [👨‍💻 docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development and contribution guide |
| [🚀 docs/PRODUCTION.md](docs/PRODUCTION.md) | Production deployment guide |

## 🔄 Migration from Legacy

If you're upgrading from an older version with global `LOCAL_ROUTER_MODE`:

```bash
# Automatic migration
curl -X POST http://localhost:8004/admin/migrate-from-global-mode \
     -H "X-Service-Token: your_token"

# The system automatically converts:
# LOCAL_ROUTER_MODE=true  + has router  → connection_method="router"
# LOCAL_ROUTER_MODE=false + any service → connection_method="rest"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### 🐛 **Reporting Issues**

- **Bug Reports**: Use issue templates with system info
- **Feature Requests**: Describe use case and benefits
- **Security Issues**: Email maintainers directly

## 📄 License

This project is licensed under the **Apache License 2.0** with an additional attribution requirement for derivative services.

**TL;DR**: You can use, modify, and distribute this software freely. If you create a service based on RssBot, please include attribution.

See [LICENSE](LICENSE) for full details.

## 🙏 Acknowledgments

- **FastAPI** for the amazing web framework
- **aiogram** for Telegram Bot API integration
- **Redis** for high-performance caching
- **SQLModel** for modern database operations
- **The open source community** for inspiration and support

## 📞 Support & Community

- **🐛 Issues**: [GitHub Issues](https://github.com/your-username/rssbot-platform/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-username/rssbot-platform/discussions)
- **📖 Wiki**: [Documentation Wiki](https://github.com/your-username/rssbot-platform/wiki)
- **📧 Security**: security@rssbot-platform.com

---

<div align="center">

**Built with ❤️ for the RSS and Telegram community**

[⭐ Star us on GitHub](https://github.com/your-username/rssbot-platform) | [🐛 Report Bug](https://github.com/your-username/rssbot-platform/issues) | [💡 Request Feature](https://github.com/your-username/rssbot-platform/issues)

</div>