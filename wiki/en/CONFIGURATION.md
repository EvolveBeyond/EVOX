# Configuration Guide

This guide covers all configuration options for the RSS Bot platform, including environment variables, service-specific settings, and deployment configurations.

## 📋 Environment Configuration

### Core Environment Variables

#### Required Settings
```bash
# Telegram Bot Configuration (REQUIRED)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
# Get this from @BotFather on Telegram

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://rssbot:password@localhost:5432/rssbot
# Format: postgresql://user:password@host:port/database
# SQLite alternative: sqlite:///./rssbot.db

# Service Communication Mode (REQUIRED)
LOCAL_ROUTER_MODE=true
# true  = Router mode (single process, low latency)
# false = REST mode (distributed services)

# Service Security (REQUIRED)
SERVICE_TOKEN=dev_service_token_change_in_production
# Use a strong, unique token for production
```

#### Optional Settings
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
# Required for background jobs and caching

# Application Environment
ENVIRONMENT=development
# Options: development, testing, staging, production

# Logging Configuration
LOG_LEVEL=DEBUG
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Telegram Advanced Settings
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
TELEGRAM_WEBHOOK_MODE=false
# true = webhook mode (production), false = polling mode (development)

# AI Service Configuration
OPENAI_API_KEY=your_openai_api_key
AI_MODEL=gpt-3.5-turbo
# Used for AI-powered content enhancement

# Payment Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
TELEGRAM_PAYMENTS_PROVIDER_TOKEN=your_telegram_payments_token
```

### Service Port Configuration

#### Default Ports
```bash
# Infrastructure Services
DB_SERVICE_PORT=8001
CONTROLLER_SERVICE_PORT=8004
BOT_SERVICE_PORT=8002
PAYMENT_SERVICE_PORT=8003
AI_SERVICE_PORT=8005

# Domain Services
FORMATTING_SERVICE_PORT=8006
CHANNEL_MGR_SERVICE_PORT=8007
USER_SERVICE_PORT=8008
MINIAPP_SERVICE_PORT=8009

# Custom Services
EXAMPLE_SERVICE_PORT=8010
```

#### Service URLs (REST Mode Only)
```bash
# Inter-service communication URLs
DB_SERVICE_URL=http://localhost:8001
BOT_SERVICE_URL=http://localhost:8002
USER_SERVICE_URL=http://localhost:8008
FORMATTING_SERVICE_URL=http://localhost:8006
CHANNEL_MGR_SERVICE_URL=http://localhost:8007
PAYMENT_SERVICE_URL=http://localhost:8003
AI_SERVICE_URL=http://localhost:8005
MINIAPP_SERVICE_URL=http://localhost:8009

# In Docker: replace localhost with service names
# DB_SERVICE_URL=http://db_svc:8001
```

## 🔧 Configuration Templates

### Development Configuration (.env.development)
```bash
# Development Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOCAL_ROUTER_MODE=true

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_dev_bot_token
TELEGRAM_WEBHOOK_MODE=false

# Database (Local Docker)
DATABASE_URL=postgresql://rssbot:password@localhost:5432/rssbot

# Redis (Local Docker)
REDIS_URL=redis://localhost:6379/0

# Security (Development)
SERVICE_TOKEN=dev_service_token_change_in_production

# AI (Optional)
OPENAI_API_KEY=your_openai_api_key
AI_MODEL=gpt-3.5-turbo

# Ports (Default)
CONTROLLER_SERVICE_PORT=8004
DB_SERVICE_PORT=8001
```

### Production Configuration (.env.production)
```bash
# Production Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
LOCAL_ROUTER_MODE=false

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_WEBHOOK_MODE=true
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=strong_webhook_secret

# Database (Production)
DATABASE_URL=postgresql://user:password@db-host:5432/rssbot_prod

# Redis (Production)
REDIS_URL=redis://redis-host:6379/0

# Security (Production)
SERVICE_TOKEN=super_secure_production_token_change_me

# Payment (Production)
STRIPE_SECRET_KEY=sk_live_your_live_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_production_webhook_secret

# AI (Production)
OPENAI_API_KEY=your_production_openai_key
AI_MODEL=gpt-4

# Service URLs (Kubernetes/Docker)
DB_SERVICE_URL=http://db-service:8001
BOT_SERVICE_URL=http://bot-service:8002
USER_SERVICE_URL=http://user-service:8008
# ... other service URLs
```

### Testing Configuration (.env.testing)
```bash
# Testing Environment
ENVIRONMENT=testing
LOG_LEVEL=WARNING
LOCAL_ROUTER_MODE=true

# Test Database (Isolated)
DATABASE_URL=sqlite:///./test_rssbot.db

# Test Redis
REDIS_URL=redis://localhost:6379/1

# Mock Services
TELEGRAM_BOT_TOKEN=test_bot_token
OPENAI_API_KEY=test_openai_key

# Test Ports (Avoid conflicts)
CONTROLLER_SERVICE_PORT=9004
DB_SERVICE_PORT=9001
```

## 🏗️ Service-Specific Configuration

### Database Service Configuration

#### Environment Variables
```bash
# Database Service Specific
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Migration Settings
ALEMBIC_CONFIG_PATH=alembic.ini
AUTO_MIGRATE=false  # Set true for automatic migrations
```

#### Config File (services/db_svc/config.py)
```python
from pydantic import BaseSettings

class DatabaseConfig(BaseSettings):
    database_url: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo_sql: bool = False
    
    class Config:
        env_prefix = "DB_"
```

### Bot Service Configuration

#### Environment Variables
```bash
# Bot Service Specific
BOT_WEBHOOK_PATH=/webhook
BOT_POLLING_TIMEOUT=10
BOT_MAX_CONNECTIONS=100
BOT_RATE_LIMIT_CALLS=30
BOT_RATE_LIMIT_PERIOD=60

# Telegram API Configuration
TELEGRAM_API_SERVER=https://api.telegram.org
TELEGRAM_FILE_SERVER=https://api.telegram.org/file
```

#### Config File (services/bot_svc/config.py)
```python
class BotConfig(BaseSettings):
    bot_token: str
    webhook_mode: bool = False
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    polling_timeout: int = 10
    max_connections: int = 100
    
    class Config:
        env_prefix = "BOT_"
```

### AI Service Configuration

#### Environment Variables
```bash
# AI Service Specific
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7
AI_TIMEOUT=30
AI_MAX_RETRIES=3
AI_RATE_LIMIT_RPM=60

# Usage Quotas
AI_QUOTA_FREE=1000
AI_QUOTA_PREMIUM=10000
AI_QUOTA_ENTERPRISE=100000
```

### Payment Service Configuration

#### Environment Variables
```bash
# Payment Service Specific
PAYMENT_TIMEOUT=30
PAYMENT_RETRY_ATTEMPTS=3
PAYMENT_WEBHOOK_TOLERANCE=300  # 5 minutes

# Stripe Configuration
STRIPE_WEBHOOK_TOLERANCE=300
STRIPE_MAX_NETWORK_RETRIES=2

# Plans Configuration
PREMIUM_MONTHLY_AMOUNT=999
PREMIUM_YEARLY_AMOUNT=9999
ENTERPRISE_MONTHLY_AMOUNT=4999
```

## 🔐 Security Configuration

### Authentication & Authorization

#### Service-to-Service Authentication
```bash
# Development (Simple Token)
SERVICE_TOKEN=dev_service_token_change_in_production

# Production (Strong Token)
SERVICE_TOKEN=$(openssl rand -base64 32)
# Example: kQo8VF5Q8wN8xC4zFvT1+2QzE1Nz5VGhVq8nFz3C1gI=
```

#### JWT Configuration (Future)
```bash
# JWT Settings (for production upgrade)
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_ISSUER=rssbot_platform
```

#### API Rate Limiting
```bash
# Rate Limiting (per service)
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60  # seconds
RATE_LIMIT_STORAGE=redis://localhost:6379/2
```

### Webhook Security

#### Telegram Webhooks
```bash
TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)
```

#### Payment Webhooks
```bash
# Stripe
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef

# Custom validation
PAYMENT_WEBHOOK_SIGNATURE_HEADER=X-Payment-Signature
PAYMENT_WEBHOOK_TIMESTAMP_TOLERANCE=300
```

## 🐳 Docker Configuration

### Docker Compose Environment

#### Infrastructure Services (.env.docker)
```bash
# Docker Compose Settings
POSTGRES_DB=rssbot
POSTGRES_USER=rssbot
POSTGRES_PASSWORD=secure_password_change_me
POSTGRES_PORT=5432

REDIS_PORT=6379
REDIS_PASSWORD=redis_password_change_me

# Network Configuration
DOCKER_NETWORK=rssbot_network
```

### Kubernetes Configuration

#### ConfigMap Example
```yaml
# k8s-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rssbot-config
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  LOCAL_ROUTER_MODE: "false"
  REDIS_URL: "redis://redis-service:6379/0"
  DB_SERVICE_URL: "http://db-service:8001"
```

#### Secret Example
```yaml
# k8s-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rssbot-secrets
type: Opaque
stringData:
  TELEGRAM_BOT_TOKEN: "your_bot_token"
  SERVICE_TOKEN: "your_service_token"
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
  OPENAI_API_KEY: "your_openai_key"
```

## 🔧 Advanced Configuration

### Feature Flags

#### Environment-Based Features
```bash
# Feature Toggles
ENABLE_AI_FEATURES=true
ENABLE_PAYMENT_PROCESSING=true
ENABLE_ANALYTICS=false
ENABLE_RATE_LIMITING=true
ENABLE_CACHING=true

# Experimental Features
EXPERIMENTAL_FEATURES=false
BETA_FEATURES=false
```

### Performance Tuning

#### Database Performance
```bash
# Connection Pool Tuning
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_STATEMENT_TIMEOUT=30

# Query Performance
DB_QUERY_CACHE_SIZE=1000
DB_SLOW_QUERY_THRESHOLD=1.0  # seconds
```

#### Redis Performance
```bash
# Redis Tuning
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_KEEPALIVE=true
REDIS_SOCKET_KEEPALIVE_OPTIONS=1,3,5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=50
```

### Monitoring Configuration

#### Logging
```bash
# Logging Configuration
LOG_FORMAT=json  # json, text
LOG_FILE_PATH=/var/log/rssbot/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
LOG_ROTATION=daily

# Structured Logging
ENABLE_REQUEST_LOGGING=true
ENABLE_SQL_LOGGING=false
ENABLE_PERFORMANCE_LOGGING=true
```

#### Metrics
```bash
# Metrics Collection
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics
PROMETHEUS_ENABLED=true
```

## 🔄 Configuration Management

### Environment Loading Priority

1. **Command Line Arguments** (highest priority)
2. **Environment Variables**
3. **`.env` file**
4. **Default Values** (lowest priority)

### Configuration Validation

#### Startup Validation Script
```bash
# scripts/validate_config.py
import os
import sys

def validate_config():
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL',
        'SERVICE_TOKEN'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"Missing required environment variables: {missing}")
        sys.exit(1)
    
    print("Configuration validation passed")

if __name__ == "__main__":
    validate_config()
```

### Configuration Templates

#### Generate Configuration
```bash
# scripts/generate_config.sh
#!/bin/bash

ENVIRONMENT=${1:-development}

cat > .env.${ENVIRONMENT} << EOF
# Generated configuration for ${ENVIRONMENT}
ENVIRONMENT=${ENVIRONMENT}
LOCAL_ROUTER_MODE=${LOCAL_ROUTER_MODE:-true}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-your_bot_token_here}
DATABASE_URL=${DATABASE_URL:-postgresql://rssbot:password@localhost:5432/rssbot}
SERVICE_TOKEN=$(openssl rand -base64 32)
# ... other settings
EOF

echo "Configuration generated: .env.${ENVIRONMENT}"
```

## 📊 Configuration Best Practices

### Security Best Practices

1. **Never commit secrets**: Use `.env` files that are gitignored
2. **Rotate tokens regularly**: Especially in production
3. **Use strong passwords**: Generate with `openssl rand -base64 32`
4. **Separate environments**: Different tokens for dev/staging/prod
5. **Validate input**: Check configuration values at startup

### Deployment Best Practices

1. **Environment-specific configs**: Different settings per environment
2. **Configuration validation**: Fail fast on invalid config
3. **Default values**: Sensible defaults for optional settings
4. **Documentation**: Document all configuration options
5. **Version configuration**: Track configuration changes

This configuration guide provides a comprehensive overview of all available settings. For specific deployment scenarios, refer to the [Production Guide](PRODUCTION.md) and [Docker Wiki](../wiki/DOCKER.md).