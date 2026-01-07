"""
Advanced Intent System Demo
===========================

Demonstrates the new modular Intent System with both Data Intents and 
Operation Intents working together. Shows backward compatibility plus
new custom intent capabilities.

Features demonstrated:
- Built-in data intents (EPHEMERAL, STANDARD, CRITICAL)
- Custom data intents with inline configuration
- Operation intents for endpoint categorization
- Combined intent processing
- Backward compatibility with existing code
"""

from evox import service, get, post, Body, Param
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

# Import new intent systems
from evox.core.data.intents.data_intents import (
    BuiltInDataIntent, CustomIntentConfig, register_custom_data_intent
)
from evox.core.data.intents.operation_intents import (
    OperationIntent, user_management, analytics, payment
)

# Register custom data intents
password_masked_config = CustomIntentConfig(
    intent_name="PASSWORD_MASKED",
    encrypt=True,
    cache_enabled=False,
    audit_logging=True,
    custom_properties={
        "mask_in_logs": True,
        "no_display": True
    }
)
register_custom_data_intent("PASSWORD_MASKED", password_masked_config)

reliable_storage_config = CustomIntentConfig(
    intent_name="RELIABLE_STORAGE", 
    strong_consistency=True,
    replication_required=True,
    cache_enabled=False,
    task_priority="high",
    emergency_buffer=True,
    custom_properties={
        "delayed_ok": True
    }
)
register_custom_data_intent("RELIABLE_STORAGE", reliable_storage_config)


# === Data Intent Examples ===

class UserModel(BaseModel):
    """
    Model demonstrating various data intent approaches
    """
    # Built-in intents (backward compatible)
    id: int = Field(
        ..., 
        description="User ID",
        json_schema_extra={"intent": "EPHEMERAL"}  # String form works
    )
    
    # New explicit built-in intent
    username: str = Field(
        ..., 
        description="Username",
        json_schema_extra={"data_intent": BuiltInDataIntent.STANDARD}
    )
    
    # Custom intent by name
    email: str = Field(
        ..., 
        description="Email address",
        json_schema_extra={"data_intent": "PASSWORD_MASKED"}
    )
    
    # Inline custom configuration
    ssn: str = Field(
        ..., 
        description="Social Security Number",
        json_schema_extra={
            "data_intent": "SENSITIVE_DATA",
            "intent_config": {
                "encrypt": True,
                "audit_logging": True,
                "cache_enabled": False,
                "custom_properties": {
                    "pii": True,
                    "mask_in_response": True
                }
            }
        }
    )
    
    # Operation-critical data
    account_balance: float = Field(
        ..., 
        description="Account balance",
        json_schema_extra={"data_intent": "RELIABLE_STORAGE"}
    )


# === Operation Intent Examples ===

@user_management(priority="high")
@get("/users/{user_id}")
async def get_user(user_id: int = Param(int)) -> Dict[str, Any]:
    """User management endpoint with high priority"""
    return {
        "user_id": user_id,
        "name": "John Doe",
        "intent_processed": "Operation intent applied"
    }

@analytics(sample_rate=0.1)
@get("/analytics/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """Analytics endpoint with sampling"""
    return {
        "active_users": 1250,
        "revenue": 45000,
        "intent_processed": "Analytics intent with sampling"
    }

@payment(tracing_enabled=True)
@post("/payments/process")
async def process_payment(request: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Payment processing with enhanced tracing"""
    return {
        "transaction_id": "txn_12345",
        "status": "processed",
        "amount": request.get("amount", 0),
        "intent_processed": "Payment intent with tracing"
    }


# === Combined Intent Example ===

class TransactionRequest(BaseModel):
    """
    Model showing combined data and operation intents
    """
    # Data-level intents
    user_id: int = Field(
        ..., 
        json_schema_extra={"data_intent": BuiltInDataIntent.CRITICAL}
    )
    
    amount: float = Field(
        ..., 
        json_schema_extra={"data_intent": BuiltInDataIntent.STANDARD}
    )
    
    card_number: str = Field(
        ..., 
        json_schema_extra={
            "data_intent": "PAYMENT_DATA",
            "intent_config": {
                "encrypt": True,
                "audit_logging": True,
                "cache_enabled": False
            }
        }
    )

@payment(priority="highest", auth_required=True)
@post("/transactions")
async def create_transaction(
    request: TransactionRequest = Body(...)
) -> Dict[str, Any]:
    """
    Transaction endpoint demonstrating combined intent processing.
    
    Operation intent: PAYMENT (routes to high-priority queue, enables tracing)
    Data intents: Various field-level intents for different processing rules
    """
    return {
        "transaction_id": f"txn_{datetime.now().timestamp()}",
        "user_id": request.user_id,
        "amount": request.amount,
        "status": "completed",
        "processing_info": {
            "operation_intent": "PAYMENT",
            "data_intents_processed": [
                "CRITICAL (user_id)",
                "STANDARD (amount)", 
                "CUSTOM_ENCRYPTED (card_number)"
            ]
        }
    }


# === Backward Compatibility Test ===

class LegacyUserModel(BaseModel):
    """
    Model using legacy Intent enum (still works)
    """
    name: str = Field(
        ..., 
        json_schema_extra={"intent": "CRITICAL"}  # Legacy string form
    )
    
    temp_token: str = Field(
        ..., 
        json_schema_extra={"intent": "EPHEMERAL"}  # Legacy enum value
    )

@get("/legacy/test")
async def legacy_test() -> Dict[str, Any]:
    """Endpoint using legacy intent system (still works)"""
    return {
        "message": "Legacy intent system working",
        "backward_compatible": True
    }


# Create service
svc = service("intent-demo").port(8002).build()


def main():
    print("🚀 Advanced Intent System Demo")
    print("=" * 40)
    print()
    print("🎯 New Features Demonstrated:")
    print("✅ Built-in Data Intents: EPHEMERAL, STANDARD, CRITICAL")
    print("✅ Custom Data Intents: PASSWORD_MASKED, RELIABLE_STORAGE")
    print("✅ Inline Intent Configuration: Direct config in Field()")
    print("✅ Operation Intents: @user_management, @analytics, @payment")
    print("✅ Combined Processing: Data + Operation intents together")
    print("✅ Backward Compatibility: Legacy code still works")
    print()
    print("📋 Endpoints Available:")
    print("GET  /users/{user_id}           - User management (high priority)")
    print("GET  /analytics/dashboard       - Analytics (sampled)")  
    print("POST /payments/process          - Payment processing (traced)")
    print("POST /transactions              - Combined intent processing")
    print("GET  /legacy/test               - Backward compatibility test")
    print()
    print("💡 Usage Examples:")
    print("# Built-in intent")
    print('Field(..., json_schema_extra={"data_intent": BuiltInDataIntent.CRITICAL})')
    print()
    print("# Custom intent by name")  
    print('Field(..., json_schema_extra={"data_intent": "PASSWORD_MASKED"})')
    print()
    print("# Inline configuration")
    print('Field(..., json_schema_extra={"intent_config": {"encrypt": True, "audit": True}})')
    print()
    print("# Operation intent decorator")
    print('@user_management(priority="high")')
    print('async def endpoint(): ...')


if __name__ == "__main__":
    main()
    # Uncomment to run: svc.run(dev=True)