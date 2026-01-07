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
- evox run project [--dev] (Run entire project)
- evox run service <name> [--dev] (Run specific service)
- evox run plugin <name> [--dev] (Run specific plugin)
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

run_app = typer.Typer(help="Run EVOX components")
app.add_typer(run_app, name="run")


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
def new_plugin(name: str, plugin_type: str = typer.Option("generic", "--type", help="Type of plugin to create (e.g., storage)")):
    """Create a new plugin template."""
    plugin_manager = get_plugin_manager()
    success = plugin_manager.create_plugin_template(name, plugin_type=plugin_type)
    
    if success:
        typer.secho(f"✅ Created {plugin_type} plugin template '{name}'", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Failed to create {plugin_type} plugin template '{name}'", fg=typer.colors.RED)


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


@run_app.command("project")
def run_project(dev: bool = typer.Option(False, "--dev", "-d", help="Run in development mode with auto-reload")):
    """Run the entire EVOX project with all services."""
    from evox.core.orchestrator import orchestrator
    import asyncio
    
    typer.secho(f"🚀 Running EVOX project in {'development' if dev else 'production'} mode", fg=typer.colors.BLUE, bold=True)
    
    try:
        # Run the orchestrator
        asyncio.run(orchestrator.run(dev=dev))
    except KeyboardInterrupt:
        typer.secho("\n⚠️  Project stopped by user", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"❌ Error running project: {e}", fg=typer.colors.RED)


@run_app.command("service")
def run_service(name: str, dev: bool = typer.Option(False, "--dev", "-d", help="Run in development mode with auto-reload")):
    """Run a specific service by name."""
    project_manager = get_project_manager()
    services = project_manager.list_services()
    
    # Find the service
    target_service = None
    for service in services:
        if service["name"] == name:
            target_service = service
            break
    
    if not target_service:
        typer.secho(f"❌ Service '{name}' not found", fg=typer.colors.RED)
        return
    
    typer.secho(f"🚀 Running service '{name}' in {'development' if dev else 'production'} mode", fg=typer.colors.BLUE, bold=True)
    
    try:
        # Add service path to Python path temporarily
        import sys
        service_path = target_service["path"]
        if service_path not in sys.path:
            sys.path.insert(0, service_path)
        
        # Import and run the service
        import importlib.util
        main_py = f"{service_path}/main.py"
        spec = importlib.util.spec_from_file_location(f"{name}_module", main_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for the service instance and run it
        if hasattr(module, "svc"):
            service_instance = module.svc
            service_instance.run(dev=dev)
        else:
            typer.secho(f"❌ Service '{name}' does not have a service instance (svc)", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"❌ Error running service '{name}': {e}", fg=typer.colors.RED)


@run_app.command("plugin")
def run_plugin(name: str, dev: bool = typer.Option(False, "--dev", "-d", help="Run in development mode")):
    """Run a specific plugin by name."""
    plugin_manager = get_plugin_manager()
    plugins = plugin_manager.list_plugins()
    
    # Find the plugin
    target_plugin = None
    for plugin in plugins:
        if plugin["name"] == name:
            target_plugin = plugin
            break
    
    if not target_plugin:
        typer.secho(f"❌ Plugin '{name}' not found", fg=typer.colors.RED)
        return
    
    typer.secho(f"🔌 Running plugin '{name}'", fg=typer.colors.BLUE, bold=True)
    typer.secho("Note: Plugins are typically loaded by services, not run directly", fg=typer.colors.YELLOW)
    
    try:
        # Add plugin path to Python path temporarily
        import sys
        plugin_path = target_plugin["path"]
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)
        
        # Import and run the plugin
        import importlib.util
        main_py = f"{plugin_path}/main.py"
        spec = importlib.util.spec_from_file_location(f"{name}_module", main_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Execute the plugin if it has a main execution block
        if hasattr(module, "main"):
            module.main()
        elif hasattr(module, "__main__"):
            module.__main__()
        else:
            typer.secho(f"ℹ️  Plugin '{name}' loaded successfully but has no main execution function", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"❌ Error running plugin '{name}': {e}", fg=typer.colors.RED)


@app.command("run")
def run_all(dev: bool = typer.Option(False, "--dev", "-d", help="Run in development mode with auto-reload")):
    """Run the entire EVOX project (alias for run project)."""
    run_project(dev=dev)


if __name__ == "__main__":
    app()