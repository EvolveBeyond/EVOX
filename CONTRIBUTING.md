# Contributing to EVOX v0.2.3_Beta

Welcome! We're excited that you're interested in contributing to EVOX. This document provides guidelines and information to help you get started with the **v0.2.3_Beta** release, optimized for **Python 3.13+**.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please treat everyone with respect and kindness.

## How to Contribute

### Reporting Issues

Before reporting an issue, please check if it has already been reported. When reporting a new issue:

1. **Use a clear and descriptive title**
2. **Provide a detailed description** of the problem
3. **Include steps to reproduce** the issue
4. **Specify your environment** (OS, Python version, EVOX version)
5. **Include relevant code snippets** or configuration files

### Suggesting Enhancements

We welcome ideas for new features! When suggesting an enhancement:

1. **Check if it's already planned** in our roadmap
2. **Explain the problem** your suggestion solves
3. **Describe your proposed solution**
4. **Consider alternatives** and trade-offs
5. **Indicate if you'd like to implement it**

### Code Contributions

#### Getting Started

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Make your changes
4. Write tests if applicable
5. Ensure all tests pass
6. Submit a pull request

#### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/evox.git
cd evox

# Install Rye (if not already installed)
curl -sSf https://rye.astral.sh/get | bash

# Sync dependencies with Rye
rye sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Rye-First Workflow

EVOX follows a **Rye-first** development workflow:

1. **Sync dependencies**: `rye sync` - Install all dependencies
2. **Run tests**: `rye test` or `rye run pytest` - Execute test suite
3. **Build package**: `rye build` - Create distribution packages
4. **Run commands**: `rye run <command>` - Execute development commands

#### Architecture Philosophy: Core-CLI Separation

EVOX follows the "Core-as-Brain, CLI-as-Shell" principle:
- **All business logic** resides in `evox.core` (e.g., `project_manager`, `plugin_manager`)
- **CLI only handles** file I/O and command routing via method calls to the core
- **CLI should never** contain internal logic for dependency resolution or plugin states
- **Core managers** implement all functionality and are called by CLI commands

#### Coding Standards

- Follow PEP 8 style guide
- Write clear, descriptive docstrings for all public APIs
- **Mandatory:** Use Python 3.13+ idioms:
  - Use `|` for union types (PEP 604): `str | int` instead of `Union[str, int]`
  - Use `X | None` instead of `Optional[X]`
  - Apply modern Type Parameter syntax where applicable
- Include type hints where appropriate
- Keep functions focused and small
- Write comprehensive comments for complex logic
- **Required:** All new `pluggable_services` must include comprehensive docstrings

#### Testing

- Write unit tests for new functionality
- Ensure all existing tests pass
- Run tests with: `rye test` or `rye run pytest`

### Pull Request Process

1. **Ensure your PR addresses a single issue or feature**
2. **Write a clear description** of your changes
3. **Reference any related issues** (e.g., "Fixes #123")
4. **Include tests** for new functionality
5. **Update documentation** if needed
6. **Be responsive** to feedback during review

## Proposing Changes

### New Ideas vs Implementation Changes

#### New Ideas (Architecture, Features, Concepts)

For proposing new architectural ideas, major features, or conceptual changes:

1. **Open a GitHub Discussion** in the "Ideas" category
2. **Explain the problem** you're trying to solve
3. **Describe your proposal** in detail
4. **Consider trade-offs** and alternatives
5. **Engage with the community** for feedback

This approach allows for discussion before significant implementation work begins.

#### Implementation Changes (Bug Fixes, Refactoring, Small Features)

For concrete implementation changes:

1. **Open a GitHub Issue** describing the problem
2. **Submit a Pull Request** with your solution
3. **Include tests** and documentation updates
4. **Address feedback** during code review

### Good First Issues

Looking for a good way to start contributing? Check out issues labeled "good first issue". These are typically:

- Well-defined and scoped
- Require minimal knowledge of the codebase
- Have clear acceptance criteria
- Are suitable for newcomers

**New to EVOX?** Start with issues tagged with `python-3.13`, `typing-enhancement`, or `docstring-needed`.

## Architecture Overview

### Core Components

1. **ProjectManager** - Project structure and configuration management
2. **PluginManager** - Pluggable service discovery and loading
3. **Lifecycle** - Event bus and lifecycle hook system
4. **Data IO** - Intent-aware unified data interface
5. **Service Registry** - Service discovery and communication
6. **CLI** - Command-line interface

### Design Principles

1. **Data-Intent-Aware** - Behavior inferred from declared intents
2. **Zero Dependencies by Default** - In-memory storage unless explicitly configured
3. **Fluent API** - Method chaining for clean, readable code
4. **Escape Hatches** - Access to underlying FastAPI when needed
5. **Rye-Native** - Designed for modern Python package management

## Documentation

Improving documentation is one of the most valuable contributions you can make!

### Types of Documentation

1. **API Reference** - Docstrings for all public APIs
2. **User Guides** - Tutorials and how-to guides
3. **Conceptual Guides** - Explanations of architecture and design
4. **Examples** - Practical code samples

### Writing Style

- Use clear, simple language
- Include practical examples
- Explain "why" as well as "how"
- Keep sections focused and scannable

## Community

### Communication Channels

- **GitHub Discussions** - For general discussion and questions
- **GitHub Issues** - For bug reports and specific feature requests
- **Twitter** - For announcements and quick updates (if available)

### Recognition

Contributors are recognized in:

1. **Release notes** for each version
2. **Contributors list** in documentation
3. **GitHub Sponsors** (when available)

## Questions?

If you have any questions about contributing, feel free to:

1. Open a GitHub Discussion
2. Ask in relevant issues
3. Contact maintainers directly

Thank you for contributing to EVOX! 🙏

---

*EVOX is in Beta. Built for resilience and production-grade intelligence. The framework is stable for production use with comprehensive documentation and examples.*