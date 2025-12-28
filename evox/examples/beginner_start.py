"""
Hello EVOX - Beginner's Kickstart
=================================

The absolute simplest way to see EVOX in action.
No complex folder structure, just one file to get you started quickly!

This example shows both functional and class-based approaches
to demonstrate EVOX's flexibility from day one.
"""

from evox import service, get, post, Body, Param
from typing import Dict, Any
from pydantic import BaseModel, Field
from typing import Annotated
from evox.core.intents import Intent


# Functional Service Example (Pydantic-Enhanced)
# ===========================================
# The simplest possible EVOX service with intent-aware Pydantic models
@get("/hello/{name}")
async def hello(name: str = Param(str)) -> Dict[str, str]:
    return {"message": f"Hello, {name}! Welcome to EVOX"}


# Intent-Aware Echo Model
class EchoRequest(BaseModel):
    """
    Intent-Aware Echo Request Model
    
    Demonstrates how field-level intents influence EVOX behavior:
    - message field marked as EPHEMERAL gets optimized caching
    """
    message: str = Field(
        ..., 
        description="Message to echo back",
        json_schema_extra={"intent": Intent.EPHEMERAL}
    )
    metadata: Dict[str, Any] | None = Field(
        None,
        description="Optional metadata",
        json_schema_extra={"intent": Intent.LAZY}
    )


@post("/echo")
async def echo(request: EchoRequest = Body(...)) -> Dict[str, Any]:
    """
    Intent-aware echo endpoint.
    
    EVOX automatically processes this request based on the model's declared intents.
    """
    return {
        "received": request.message, 
        "metadata": request.metadata,
        "message": "Echoed back successfully",
        "processing": "intent-aware"
    }


# Class-Based Service Example (Intent-Aware)
# ==========================================
# A more structured approach with Pydantic models and intent awareness
from evox import Controller, GET, POST


class UserCreateRequest(BaseModel):
    """
    Intent-Aware User Creation Request Model
    
    Demonstrates how field-level intents influence EVOX behavior:
    - email marked as SENSITIVE gets encrypted storage
    - name marked as CRITICAL gets strong consistency
    """
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="User's full name",
        json_schema_extra={"intent": Intent.CRITICAL}
    )
    email: str = Field(
        ..., 
        pattern=r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$', 
        description="Sensitive email address (encrypted storage)",
        json_schema_extra={"intent": Intent.SENSITIVE}
    )
    age: int | None = Field(
        None, 
        ge=0, 
        le=150, 
        description="Age in years",
        json_schema_extra={"intent": Intent.EPHEMERAL}
    )


@Controller("/api/v1/users", tags=["users"])
class UserService:
    @GET("/{user_id:int}")
    async def get_user(self, user_id: int = Param(int)) -> Dict[str, str]:
        return {"id": user_id, "name": f"User {user_id}", "service": "class-based"}
    
    @POST("/")
    async def create_user(self, user_data: UserCreateRequest = Body(...)) -> Dict:
        return {"status": "created", "user": user_data.model_dump(), "service": "class-based"}


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