"""
Data Intent Service - Pluggable Core Service

This service demonstrates:
- Pluggable service architecture
- Type-safe dependency injection
- Data intent management
- Environmental intelligence integration
"""

from evoid import service, get, post, put, delete, Param, Body, Intent
from evoid.core.inject import inject
from evoid.core.intelligence import get_environmental_intelligence
from pydantic import BaseModel
from typing import Annotated, Optional, Dict, Any
import json

# Define data models for intent management
class IntentDefinition(BaseModel):
    """Definition of a data intent"""
    name: str
    description: str
    ttl: int = 300
    cacheable: bool = True
    consistency: str = "eventual"  # eventual, strong
    priority: str = "medium"  # high, medium, low

class IntentUpdateRequest(BaseModel):
    """Request to update an intent definition"""
    description: Optional[str] = None
    ttl: Optional[int] = None
    cacheable: Optional[bool] = None
    consistency: Optional[str] = None
    priority: Optional[str] = None

# In-memory storage for intent definitions
intents_db: Dict[str, IntentDefinition] = {}

# Create service with type-safe registration
svc = service("data-intent-service").port(8004).build()

# Type-safe dependency injection examples
class IntentManagementService:
    """Service for managing data intents"""
    
    async def get_intent(self, intent_name: str) -> Optional[IntentDefinition]:
        """Get an intent definition by name"""
        return intents_db.get(intent_name)
    
    async def create_intent(self, intent: IntentDefinition) -> IntentDefinition:
        """Create a new intent definition"""
        intents_db[intent.name] = intent
        return intent
    
    async def update_intent(self, intent_name: str, updates: IntentUpdateRequest) -> Optional[IntentDefinition]:
        """Update an existing intent definition"""
        if intent_name not in intents_db:
            return None
        
        intent = intents_db[intent_name]
        
        # Apply updates
        if updates.description is not None:
            intent.description = updates.description
        if updates.ttl is not None:
            intent.ttl = updates.ttl
        if updates.cacheable is not None:
            intent.cacheable = updates.cacheable
        if updates.consistency is not None:
            intent.consistency = updates.consistency
        if updates.priority is not None:
            intent.priority = updates.priority
        
        intents_db[intent_name] = intent
        return intent
    
    async def delete_intent(self, intent_name: str) -> bool:
        """Delete an intent definition"""
        if intent_name in intents_db:
            del intents_db[intent_name]
            return True
        return False
    
    async def list_intents(self) -> Dict[str, IntentDefinition]:
        """List all intent definitions"""
        return intents_db.copy()

# GET endpoint to retrieve an intent definition
@get("/intents/{intent_name}")
@Intent(cacheable=True, ttl=300)  # Cacheable with 5-minute TTL
async def get_intent(intent_name: Annotated[str, Param]):
    """Retrieve an intent definition by name"""
    # Type-safe dependency injection
    intent_svc = inject(IntentManagementService)
    intent = await intent_svc.get_intent(intent_name)
    
    if intent:
        return intent
    else:
        return {"error": "Intent not found"}, 404

# POST endpoint to create a new intent definition
@post("/intents")
@Intent(consistency="strong")  # Strong consistency for creation
async def create_intent(intent_data: Annotated[IntentDefinition, Body]):
    """Create a new intent definition"""
    # Type-safe dependency injection
    intent_svc = inject(IntentManagementService)
    
    # Check if intent already exists
    existing = await intent_svc.get_intent(intent_data.name)
    if existing:
        return {"error": "Intent already exists"}, 409
    
    created_intent = await intent_svc.create_intent(intent_data)
    return {"message": "Intent created", "intent": created_intent}, 201

# PUT endpoint to update an existing intent definition
@put("/intents/{intent_name}")
@Intent(consistency="strong")  # Strong consistency for updates
async def update_intent(
    intent_name: Annotated[str, Param], 
    update_data: Annotated[IntentUpdateRequest, Body]
):
    """Update an existing intent definition"""
    # Type-safe dependency injection
    intent_svc = inject(IntentManagementService)
    
    updated_intent = await intent_svc.update_intent(intent_name, update_data)
    if updated_intent:
        return {"message": "Intent updated", "intent": updated_intent}
    else:
        return {"error": "Intent not found"}, 404

# DELETE endpoint to remove an intent definition
@delete("/intents/{intent_name}")
@Intent(consistency="strong")  # Strong consistency for deletion
async def delete_intent(intent_name: Annotated[str, Param]):
    """Delete an intent definition"""
    # Type-safe dependency injection
    intent_svc = inject(IntentManagementService)
    
    success = await intent_svc.delete_intent(intent_name)
    if success:
        return {"message": "Intent deleted"}
    else:
        return {"error": "Intent not found"}, 404

# GET endpoint to list all intent definitions
@get("/intents")
@Intent(cacheable=True, ttl=120)  # Cacheable with 2-minute TTL
async def list_intents():
    """List all intent definitions"""
    # Type-safe dependency injection
    intent_svc = inject(IntentManagementService)
    intents = await intent_svc.list_intents()
    return {"intents": intents, "count": len(intents)}

# GET endpoint to analyze system intelligence for intent optimization
@get("/analyze/intents")
@Intent(cacheable=True, ttl=60)  # Cacheable with 1-minute TTL
async def analyze_intents():
    """Analyze system intelligence for intent optimization"""
    # Get environmental intelligence
    env_intel = get_environmental_intelligence()
    load_factor = env_intel.get_system_load_factor()
    
    # Analyze intent usage patterns (mock implementation)
    intent_count = len(intents_db)
    
    recommendations = []
    if load_factor > 0.8:
        recommendations.append("High system load detected - consider increasing TTL for cacheable intents")
    elif load_factor < 0.3:
        recommendations.append("Low system load - can optimize cache strategies for better performance")
    
    if intent_count > 50:
        recommendations.append(f"Large number of intents ({intent_count}) - consider consolidation")
    
    return {
        "message": "Intent analysis completed",
        "intent_count": intent_count,
        "system_load": round(load_factor, 2),
        "recommendations": recommendations,
        "analysis_timestamp": "current"
    }

if __name__ == "__main__":
    svc.run(dev=True)