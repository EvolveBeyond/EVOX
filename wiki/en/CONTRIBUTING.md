# Contributing to RSS Bot Platform

Thank you for your interest in contributing to the RSS Bot platform! This guide will help you get started with contributing code, documentation, and improvements.

## 🤝 How to Contribute

### Types of Contributions

1. **Bug Reports** - Report issues and bugs
2. **Feature Requests** - Suggest new features
3. **Code Contributions** - Submit bug fixes and new features
4. **Documentation** - Improve guides and API docs
5. **Testing** - Write tests and improve test coverage
6. **Performance** - Optimize code and improve efficiency

### Getting Started

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/yourusername/RssBot.git
   cd RssBot
   ```

2. **Set Up Development Environment**
   ```bash
   # Follow the Getting Started guide
   cp .env.example .env
   # Edit .env with your configuration
   rye sync
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-number
   ```

## 🛠️ Development Guidelines

### Code Style

#### Python Code Standards
- **Formatting**: Use `black` for code formatting
- **Import Sorting**: Use `isort` for import organization
- **Linting**: Follow `flake8` guidelines
- **Type Hints**: Add type hints for new code

```bash
# Format your code before committing
rye run black services/
rye run isort services/
rye run flake8 services/
```

#### Service Architecture Patterns
- Follow the existing router pattern for new services
- Implement both standalone and router-compatible modes
- Include proper error handling and logging
- Add comprehensive docstrings

```python
# Example service structure
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "my_service"}

async def initialize_service():
    """Initialize service resources."""
    print("My service initialized")

def register_with_controller(controller_app):
    """Register with controller for router mode."""
    controller_app.include_router(router, prefix="/my-service")
```

### Documentation Standards

#### Code Documentation
- Add docstrings to all public functions
- Include type hints for parameters and return values
- Document complex business logic with inline comments

```python
async def process_rss_feed(
    feed_url: str,
    channel_config: Dict[str, Any],
    max_items: int = 10
) -> List[ProcessedItem]:
    """
    Process RSS feed and return formatted items.
    
    Args:
        feed_url: URL of the RSS feed to process
        channel_config: Channel-specific configuration
        max_items: Maximum number of items to process
        
    Returns:
        List of processed feed items ready for publishing
        
    Raises:
        ValueError: If feed_url is invalid
        HTTPException: If feed cannot be fetched
    """
    pass
```

#### API Documentation
- Update OpenAPI schemas when adding endpoints
- Include request/response examples
- Document all error responses

### Testing Requirements

#### Test Coverage
- Write unit tests for new functions
- Add integration tests for API endpoints
- Ensure tests pass in both router and REST modes

```python
# Example test structure
import pytest
from fastapi.testclient import TestClient
from services.my_svc.router import router

@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## 📝 Contribution Workflow

### 1. Issue Creation

#### Bug Reports
Use the bug report template:
```markdown
**Bug Description**
A clear description of the bug.

**Steps to Reproduce**
1. Step one
2. Step two
3. See error

**Expected Behavior**
What should happen.

**Environment**
- OS: [e.g., Arch Linux]
- Python version: [e.g., 3.11.6]
- Deployment mode: [Router/REST]

**Logs**
Relevant error logs or screenshots.
```

#### Feature Requests
```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches you've thought about.
```

### 2. Development Process

#### Branch Naming
- `feature/feature-name` - New features
- `bugfix/issue-number` - Bug fixes
- `docs/topic` - Documentation updates
- `test/component` - Test improvements

#### Commit Messages
Follow conventional commit format:
```bash
feat(user-service): add user preference management
fix(bot): resolve webhook authentication issue
docs(api): update authentication documentation
test(db): add database connection tests
```

### 3. Pull Request Process

#### Before Submitting
```bash
# Ensure your code is properly formatted
rye run black services/
rye run isort services/

# Run linting
rye run flake8 services/

# Run tests (when available)
rye run pytest tests/

# Test both deployment modes
LOCAL_ROUTER_MODE=true ./scripts/test_router_mode.sh
LOCAL_ROUTER_MODE=false ./scripts/smoke_test.sh
```

#### Pull Request Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Test coverage improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Both router and REST modes tested

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## 🏗️ Architecture Guidelines

### Adding New Services

#### 1. Service Structure
```bash
# Create new service directory
mkdir services/new_svc

# Required files
touch services/new_svc/router.py    # FastAPI router
touch services/new_svc/main.py      # Standalone app
touch services/new_svc/config.py    # Service configuration
touch services/new_svc/__init__.py  # Python package
```

#### 2. Router Implementation
```python
# services/new_svc/router.py
from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Optional
import os

# Security middleware
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token

# Router setup
router = APIRouter(tags=["new_service"])

# Required functions
async def initialize_service():
    """Initialize service (called on startup)."""
    pass

def register_with_controller(controller_app):
    """Register with controller for router mode."""
    controller_app.include_router(router, prefix="/new-service")

# Required endpoints
@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "new_svc"}

@router.get("/ready") 
async def readiness_check():
    return {"status": "ready", "service": "new_svc"}
```

#### 3. Service Documentation
- Add service description to main README
- Create API documentation in `docs/API.md`
- Add configuration options to `docs/CONFIGURATION.md`

### Database Changes

#### 1. Model Updates
```python
# Add new models to services/db_svc/db/models.py
@ModelRegistry.register
class NewModel(BaseEntity, table=True):
    """Description of the new model."""
    name: str = Field(max_length=255)
    description: Optional[str] = None
    # ... other fields
```

#### 2. Migrations
```bash
# Create migration
cd services/db_svc
rye run alembic revision --autogenerate -m "Add NewModel"

# Review the generated migration
# Edit if necessary, then apply
rye run alembic upgrade head
```

## 🧪 Testing Guidelines

### Test Organization
```
tests/
├── unit/                 # Unit tests
│   ├── test_db_service.py
│   ├── test_user_service.py
│   └── test_new_service.py
├── integration/          # Integration tests
│   ├── test_service_communication.py
│   └── test_workflows.py
├── e2e/                  # End-to-end tests
│   └── test_complete_flows.py
└── fixtures/             # Test data and fixtures
    └── sample_data.py
```

### Writing Tests

#### Unit Tests
```python
# Test individual functions
def test_format_rss_content():
    input_content = "<h1>Title</h1><p>Content</p>"
    result = format_rss_content(input_content)
    assert result.formatted_text.startswith("<b>Title</b>")
    assert "#rss" in result.tags
```

#### Integration Tests
```python
# Test service interactions
async def test_user_creation_flow():
    # Create user via API
    user_data = {"telegram_id": 123, "username": "testuser"}
    response = await client.post("/users/", json=user_data)
    assert response.status_code == 200
    
    # Verify user exists
    user_id = response.json()["id"]
    user_response = await client.get(f"/users/{user_id}")
    assert user_response.json()["telegram_id"] == 123
```

## 📋 Review Process

### Code Review Checklist

#### Functionality
- [ ] Code works as intended
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] No obvious bugs or security issues

#### Architecture
- [ ] Follows existing patterns
- [ ] Proper separation of concerns
- [ ] Compatible with both deployment modes
- [ ] No breaking changes to existing APIs

#### Quality
- [ ] Code is readable and maintainable
- [ ] Appropriate comments and documentation
- [ ] No code duplication
- [ ] Performance considerations addressed

#### Testing
- [ ] Adequate test coverage
- [ ] Tests are meaningful and cover edge cases
- [ ] Tests pass consistently
- [ ] Both deployment modes tested

### Review Timeline
- **Initial Review**: Within 2-3 days
- **Follow-up**: Within 1 day of updates
- **Final Approval**: When all requirements met

## 🚀 Release Process

### Version Management
- Follow semantic versioning (SemVer)
- Tag releases in Git
- Update CHANGELOG.md with each release

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Security review completed (for major changes)
- [ ] Performance impact assessed
- [ ] Migration scripts provided (if needed)
- [ ] Deployment guide updated

## 💬 Community Guidelines

### Communication
- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code discussions
- **Documentation**: Improvements and clarifications

### Code of Conduct
- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on the technical aspects

### Getting Help
- Check existing documentation first
- Search through existing issues
- Provide detailed information when asking questions
- Be patient and respectful

Thank you for contributing to the RSS Bot platform! Your contributions help make this project better for everyone.