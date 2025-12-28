"""
Nested CLI for EVOX Framework

This CLI implements a nested command structure with Typer for a professional UX.
It acts as a thin interface that delegates all business logic to core managers.
It only handles file I/O and terminal output, with no internal logic for dependency
resolution or plugin states.

Commands:
- evox new project <name>
- evox new service <name>
- evox new plugin <name>
- evox new db <name>
- evox maintenance sync
- evox maintenance health
- evox maintenance status
"""

import typer
from pathlib import Path

import json

from evox.core.project_manager import get_project_manager, ProjectManager
from evox.core.plugin_manager import get_plugin_manager, PluginManager

# Create main app
app = typer.Typer(
    name="evox",
    help="EVOX: The Smart companion for Python 3.13+ Services",
    no_args_is_help=True
)

# Create sub-apps for nested commands
new_app = typer.Typer(help="Create new EVOX components")
app.add_typer(new_app, name="new")

maintenance_app = typer.Typer(help="Maintenance and system commands")
app.add_typer(maintenance_app, name="maintenance")


@new_app.command("project")
def new_project(name: str):
    """Setup root structure + plugins/ folder."""
    project_manager = get_project_manager()
    success = project_manager.create_project(name)
    
    if success:
        typer.secho(f"✅ Created EVOX project '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to create project '{name}'", fg=typer.colors.RED)


@new_app.command("service")
def new_service(name: str):
    """Setup service folder + config.toml."""
    project_manager = get_project_manager()
    success = project_manager.create_service(name)
    
    if success:
        typer.secho(f"✅ Created EVOX service '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to create service '{name}'", fg=typer.colors.RED)


@maintenance_app.command("sync")
def sync():
    """Calls Core to scan/install dependencies via rye."""
    plugin_manager = get_plugin_manager()
    success = plugin_manager.sync_dependencies()
    
    if success:
        typer.secho("✅ Dependencies synced successfully", fg=typer.colors.GREEN)
    else:
        typer.secho("❌ Failed to sync dependencies", fg=typer.colors.RED)


@new_app.command("plugin")
def new_plugin(name: str):
    """Create a new plugin template."""
    plugin_manager = get_plugin_manager()
    success = plugin_manager.create_plugin_template(name)
    
    if success:
        typer.secho(f"✅ Created plugin template '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to create plugin template '{name}'", fg=typer.colors.RED)


@new_app.command("db")
def new_db(name: str):
    """Add database configuration to project."""
    project_manager = get_project_manager()
    success = project_manager.add_database_config(name)
    
    if success:
        typer.secho(f"✅ Added database config '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to add database config '{name}'", fg=typer.colors.RED)


@maintenance_app.command("health")
def health():
    """Run system-wide health checks."""
    project_manager = get_project_manager()
    plugin_manager = get_plugin_manager()
    
    # Check project health
    project_status = project_manager.get_project_status()
    
    # Check services
    services = project_manager.list_services()
    
    # Check plugins
    plugins = plugin_manager.list_plugins()
    
    typer.secho("🏥 EVOX Health Check", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Project Status: {project_status.value}")
    typer.echo(f"Services: {len(services)}")
    typer.echo(f"Plugins: {len(plugins)}")
    
    # Overall health status
    if len(services) > 0 or len(plugins) > 0:
        typer.secho("✅ System is healthy", fg=typer.colors.GREEN)
    else:
        typer.secho("⚠️  No services or plugins detected", fg=typer.colors.YELLOW)


@maintenance_app.command("status")
def status():
    """Beautiful overview of services, plugins, and system load."""
    project_manager = get_project_manager()
    plugin_manager = get_plugin_manager()
    
    typer.secho("📊 EVOX Status Overview", fg=typer.colors.BLUE, bold=True)
    
    # Project status
    project_status = project_manager.get_project_status()
    typer.echo(f"Project Status: {project_status.value}")
    
    # Services table
    services = project_manager.list_services()
    if services:
        typer.echo(f"\nServices ({len(services)}):")
        typer.echo("-" * 60)
        for service in services:
            name = service["name"]
            status = service["status"].value
            path = service["path"]
            typer.echo(f"{name:<20} {status:<15} {path}")
    else:
        typer.echo("\nServices: 0")
    
    # Plugins table
    plugins = plugin_manager.list_plugins()
    if plugins:
        typer.echo(f"\nPlugins ({len(plugins)}):")
        typer.echo("-" * 60)
        for plugin in plugins:
            name = plugin["name"]
            status = plugin["status"].value
            path = plugin["path"]
            typer.echo(f"{name:<20} {status:<15} {path}")
    else:
        typer.echo("\nPlugins: 0")


if __name__ == "__main__":
    app()