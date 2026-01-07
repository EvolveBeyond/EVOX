# EVOX Examples Collection

This collection contains comprehensive examples demonstrating all capabilities of the EVOX microservice framework, ordered from basic concepts to production deployment.

## 📚 Example Progression

### Foundation Examples

#### 1. [01_hello_world.py](./01_hello_world.py) - **Getting Started**
**Perfect for:** Absolute beginners wanting to see EVOX in action immediately

**Features demonstrated:**
- Basic service creation
- Simple RESTful endpoints
- Running a service
- Parameter handling
- Request/response bodies

**What you'll learn:**
- How to create your first EVOX service
- Basic endpoint decorators (`@get`, `@post`)
- Service configuration and startup

---

#### 2. [02_comprehensive_showcase.py](./02_comprehensive_showcase.py) - **Framework Deep Dive**
**Perfect for:** Developers wanting to see ALL EVOX features working together

**Features demonstrated:**
- Advanced service configuration with modern Python 3.13+ syntax
- Data and operation intents using `Annotated` type hints
- Dependency injection
- Message bus and event handling
- Background tasks and scheduling
- Caching with TTL
- Authentication and authorization
- Performance benchmarking
- Model mapping
- Data persistence

**What you'll learn:**
- Full-stack EVOX application development
- Integration of all major framework components
- Modern Python type annotation patterns
- Real-world microservice patterns

---

#### 3. [03_intent_system.py](./03_intent_system.py) - **Advanced Intent Processing**
**Perfect for:** Teams needing sophisticated data handling and compliance

**Features demonstrated:**
- Modern intent annotations using `typing.Annotated`
- Data intents (EPHEMERAL, STANDARD, CRITICAL, SENSITIVE)
- Operation intents (user_management, analytics, payment, system_admin)
- Custom intent creation and registration
- Field-level intent processing
- Intent-based caching and encryption
- Compliance-focused configurations (PCI-DSS, GDPR)

**What you'll learn:**
- Advanced intent system with modern syntax
- Custom intent configuration
- Regulatory compliance patterns
- Fine-grained data processing control

---

### Architecture & Deployment Examples

#### 4. [04_microservices.py](./04_microservices.py) - **Distributed Systems**
**Perfect for:** Building distributed microservice architectures

**Features demonstrated:**
- Multi-service architecture
- Service discovery and registration
- Proxy-based service communication
- Cross-service messaging
- Distributed caching
- Event-driven architecture
- API gateway pattern

**What you'll learn:**
- Microservices design patterns
- Service-to-service communication
- Distributed system coordination
- Scalable architecture principles

---

#### 5. [05_enterprise_system.py](./05_enterprise_system.py) - **Production Ready**
**Perfect for:** Enterprise-grade production applications

**Features demonstrated:**
- Production-ready configuration
- Database integration (SQLite)
- Advanced authentication and authorization
- Health checks and monitoring
- Performance optimization
- Error handling and logging
- Security best practices
- Administrative endpoints
- Environmental intelligence

**What you'll learn:**
- Enterprise application development
- Production deployment considerations
- Security and compliance
- Monitoring and observability
- Operational best practices

---

#### 6. [06_project_scaffolding.py](./06_project_scaffolding.py) - **Project Structure**
**Perfect for:** Creating complete microservice project layouts

**Features demonstrated:**
- Complete project directory structure generation
- Multi-service architecture setup
- Configuration management
- Shared components organization
- Development workflow setup
- Best practices for microservice projects

**What you'll learn:**
- Professional project organization
- Microservice architecture patterns
- Configuration management strategies
- Team collaboration setup

---

#### 7. [07_docker_deployment.py](./07_docker_deployment.py) - **Production Deployment**
**Perfect for:** Deploying EVOX microservices in production

**Features demonstrated:**
- Complete Docker Compose orchestration
- Multi-service deployment with dependencies
- Load balancing with nginx
- Monitoring stack (Prometheus, Grafana)
- Health checks and restart policies
- Environment configuration
- Volume management

**What you'll learn:**
- Production deployment strategies
- Container orchestration
- Monitoring and observability setup
- Infrastructure as code
- DevOps practices

---

#### 8. [08_project_workflow.py](./08_project_workflow.py) - **Complete Project Workflow**
**Perfect for:** Understanding the complete workflow of creating projects and services

**Features demonstrated:**
- Complete project creation workflow (`evox new project <name>`)
- Service creation within projects (`evox new service <name>`)
- Generated project structure and organization
- Service integration patterns
- Inter-service communication setup
- Data sharing between services
- Service discovery and registration

**What you'll learn:**
- Complete project lifecycle from creation to deployment
- How to organize multi-service projects
- Service-to-service communication patterns
- Data sharing and integration strategies
- Project structure best practices
- Workflow automation techniques

---

#### 9. [09_cli_workflow_demo.py](./09_cli_workflow_demo.py) - **Actual CLI Workflow Demonstration**
**Perfect for:** Seeing the real commands and generated project structure

**Features demonstrated:**
- **Actual CLI commands** tested and verified
- **Real project structure** that gets generated
- **Actual file contents** of generated pyproject.toml, main.py, config.toml
- **Complete command reference** with all available evox commands
- **Real-world usage example** of creating a complete system
- **Validation results** showing successful command execution

**What you'll learn:**
- Exact CLI commands to use for project creation
- What files and directories are actually generated
- How to extend the generated code with your business logic
- Complete workflow from project creation to running services
- All available CLI commands and their purposes
- Real validation that the commands work as documented

---

## 🚀 Quick Start Guide

### Running Individual Examples

```bash
# Clone the repository
git clone <repository-url>
cd EVOX

# Install dependencies
pip install -e .

# Run any example (uncomment the app.run() line first)
python examples/01_hello_world.py
```

### Running Project Generation Examples

```bash
# Generate complete project structure
python examples/06_project_scaffolding.py

# Generate Docker Compose deployment
python examples/07_docker_deployment.py
```

### Example Requirements

Most examples can run standalone. Some advanced examples may require:

- **Redis**: For distributed caching (set `REDIS_URL` environment variable)
- **Database**: For persistence examples (SQLite used by default)
- **Environment variables**: For production examples

### Environment Setup

```bash
# For production examples
export JWT_SECRET="your-jwt-secret"
export REDIS_URL="redis://localhost:6379"
export PORT=8000
```

---

## 🎯 Learning Path Recommendations

### For Beginners:
1. Start with `01_hello_world.py` - Basic concepts
2. Progress to `02_comprehensive_showcase.py` - Framework features
3. Explore `03_intent_system.py` - Advanced patterns

### For Experienced Developers:
1. Jump to `02_comprehensive_showcase.py` - Complete feature set
2. Explore `04_microservices.py` - Distributed systems
3. Study `05_enterprise_system.py` - Production patterns
4. Use `06_project_scaffolding.py` - Project setup
5. Deploy with `07_docker_deployment.py` - Production deployment

### For Enterprise Teams:
1. Begin with `06_project_scaffolding.py` - Project structure
2. Customize with `05_enterprise_system.py` - Production template
3. Enhance with `03_intent_system.py` - Compliance requirements
4. Deploy using `07_docker_deployment.py` - Infrastructure setup
5. Scale with `04_microservices.py` - Architecture patterns

---

## 🔧 Customization Guide

Each example is designed to be:
- **Runnable** - Uncomment the `app.run()` line to execute
- **Modifiable** - Easy to adapt for your specific needs
- **Extensible** - Build upon the demonstrated patterns
- **Documented** - Clear comments explaining each component

### Common Modifications:

```python
# Change port
app = service("my-service").port(3000).build()

# Add authentication
@app.endpoint("/protected", auth_required=True)
async def protected_endpoint():
    pass

# Enable caching
@cached(ttl=timedelta(hours=1))
async def expensive_operation():
    pass
```

---

## 📖 Documentation Resources

- [Official EVOX Documentation](../docs)
- [API Reference](../docs/api)
- [Configuration Guide](../docs/configuration)
- [Deployment Guide](../docs/deployment)

---

## 🤝 Contributing

Want to add more examples? Feel free to:
1. Fork the repository
2. Add your example following the naming convention
3. Submit a pull request with documentation

---

## 📞 Support

Need help with examples?
- Open an issue on GitHub
- Join our community Discord
- Check the official documentation

---

*Last updated: January 7, 2026*