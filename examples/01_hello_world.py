"""
EVOX Hello World - Getting Started Guide
========================================

This is the simplest possible EVOX application demonstrating:
- Basic service creation
- RESTful endpoint decorators
- Running a service

Perfect for absolute beginners who want to see EVOX in action immediately.
"""

from evoid import service, get, post, Body, Param
from typing import Dict, Any


# Simple functional endpoint - the easiest way to create an API
@get("/hello/{name}")
async def hello(name: str = Param(str)) -> Dict[str, str]:
    """Simple greeting endpoint that takes a name parameter"""
    return {"message": f"Hello, {name}! Welcome to EVOX!"}


# Another simple endpoint with request body
@post("/echo")
async def echo(request: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Echo back whatever is sent in the request body"""
    return {
        "received": request,
        "message": "Echoed successfully!",
        "service": "EVOX Hello World"
    }


# Create and configure the service
app = service("hello-world-service").port(8000).build()


if __name__ == "__main__":
    print("🚀 EVOX Hello World Example")
    print("=" * 30)
    print()
    print("Available Endpoints:")
    print("  GET  /hello/{name}  - Say hello to someone")
    print("  POST /echo          - Echo back your request")
    print()
    print("To run this service:")
    print("  python 01_hello_world.py")
    print()
    print("Then visit: http://localhost:8000/docs")
    
    # Uncomment to actually run the service:
    # app.run(dev=True)