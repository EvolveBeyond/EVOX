"""
Hello EVOX - Beginner's Kickstart
=================================

The absolute simplest way to see EVOX in action.
No complex folder structure, just one file to get you started quickly!

This example shows both functional and class-based approaches
to demonstrate EVOX's flexibility from day one.
"""

from evox import service, get, post, Body, Param
from typing import Dict


# Functional Service Example (5 lines)
# ===================================
# The simplest possible EVOX service
@get("/hello/{name}")
async def hello(name: str = Param(str)) -> Dict[str, str]:
    return {"message": f"Hello, {name}! Welcome to EVOX"}

@post("/echo")
async def echo(data: Dict = Body(dict)) -> Dict:
    return {"received": data, "message": "Echoed back successfully"}


# Class-Based Service Example (10 lines)
# =====================================
# A more structured approach for when you need organization
from evox import Controller, GET, POST

@Controller("/api/v1/users", tags=["users"])
class UserService:
    @GET("/{user_id:int}")
    async def get_user(self, user_id: int = Param(int)) -> Dict[str, str]:
        return {"id": user_id, "name": f"User {user_id}", "service": "class-based"}
    
    @POST("/")
    async def create_user(self, user_data: Dict = Body(dict)) -> Dict:
        return {"status": "created", "user": user_data, "service": "class-based"}


# Create and run the service
# This uses default fallback values and requires no config.toml
svc = service("beginner-service").port(8000).build()


def main():
    """
    Run the beginner example.
    
    This demonstrates how simple it is to get started with EVOX.
    Just run: python beginner_start.py
    """
    print("🚀 Hello EVOX - Beginner's Kickstart")
    print("=" * 40)
    print()
    print("✅ Functional Service:")
    print("   GET  /hello/{name}    - Simple greeting endpoint")
    print("   POST /echo            - Echo service")
    print()
    print("✅ Class-Based Service:")
    print("   GET  /api/v1/users/{user_id} - Get user by ID")
    print("   POST /api/v1/users/          - Create new user")
    print()
    print("💡 To run this service:")
    print("   python beginner_start.py")
    print()
    print("🎯 EVOX adapts to your skill level:")
    print("   • Start simple with functions")
    print("   • Scale to classes when needed")
    print("   • Grow to enterprise systems")


if __name__ == "__main__":
    main()
    
    # Uncomment the following line to run the service:
    # svc.run(dev=True)