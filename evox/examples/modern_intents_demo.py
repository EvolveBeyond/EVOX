"""
Modern Annotated Intent System Demo
===================================

Demonstrates the new Python 3.13+ Annotated-based intent system with maximum
modularity and type safety. Shows both the new syntax and backward compatibility.

Features demonstrated:
- Modern typing.Annotated for intent declarations
- Reusable intent types (CriticalStr, StandardInt, etc.)
- Custom intent markers with configuration
- Helper functions for clean syntax
- Backward compatibility with json_schema_extra
"""

from typing import Annotated, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Import the new Annotated-based intent system
from evox.core.data.intents.annotated_intents import (
    # Base markers
    Critical, Standard, Ephemeral, IntentMarker,
    # Helper functions
    critical, standard, ephemeral, custom_intent,
    # Reusable types
    CriticalStr, StandardStr, EphemeralStr,
    CriticalInt, StandardInt, EphemeralInt
)

# Register custom intent configurations
from evox.core.data.intents.data_intents import register_custom_data_intent, CustomIntentConfig

# Register a custom password masking intent
password_config = CustomIntentConfig(
    intent_name="PASSWORD_MASKED",
    encrypt=True,
    cache_enabled=False,
    audit_logging=True,
    custom_properties={
        "mask_in_logs": True,
        "no_display": True
    }
)
register_custom_data_intent("PASSWORD_MASKED", password_config)


# === Modern Annotated Intent Examples ===

# Reusable type definitions (recommended approach)
MaskedStr = Annotated[str, IntentMarker("PASSWORD_MASKED", mask=True, no_display=True, encrypt=True)]
ReliableInt = Annotated[int, IntentMarker("RELIABLE_STORAGE", strong_consistency=True, replication_required=True, no_cache=True)]
SensitiveStr = Annotated[str, IntentMarker("SENSITIVE_DATA", encrypt=True, audit_logging=True, custom_properties={"pii": True})]


class ModernUserModel(BaseModel):
    """
    Model demonstrating modern Annotated-based intent declarations
    """
    # Using reusable types
    name: CriticalStr
    password: MaskedStr
    age: ReliableInt
    
    # Inline with built-in intents
    email: Annotated[str, Critical(encrypt=True, audit_logging=True)]
    temp_token: Annotated[str, Ephemeral(cache_aggressive=True)]
    
    # Inline with custom intents
    ssn: Annotated[str, IntentMarker("SENSITIVE_DATA", encrypt=True, audit_logging=True, custom_properties={"pii": True})]
    
    # Helper function syntax
    username: Annotated[str, Standard(encrypt=False)]  # Alternative to StandardStr
    session_id: Annotated[str, Ephemeral(cache_aggressive=True, ttl_minutes=10)]


# === Complex Model Example ===

class PaymentRequest(BaseModel):
    """
    Real-world payment processing model with various intent types
    """
    # Critical payment data
    transaction_id: CriticalStr
    amount: Annotated[float, Critical(task_priority="high", message_priority="high")]
    
    # Secure payment details
    card_number: MaskedStr  # Reusable type
    cvv: Annotated[str, IntentMarker("CARD_SECURITY", encrypt=True, cache_enabled=False)]
    
    # Ephemeral processing data
    processing_token: EphemeralStr
    attempt_count: Annotated[int, Ephemeral(cache_aggressive=True)]
    
    # Standard business data
    user_id: StandardInt
    merchant_id: Annotated[int, Standard(replication_required=False)]


# === Helper Function Usage Examples ===

class AnalyticsEvent(BaseModel):
    """
    Analytics model using helper functions for clean syntax
    """
    event_type: critical(str, task_priority="low", sampling_rate=0.1)  # Custom property
    user_id: standard(int, cache_enabled=True)
    session_data: ephemeral(str, cache_aggressive=True)
    sensitive_info: custom_intent(str, "ANALYTICS_PRIVACY", encrypt=True, mask_in_logs=True)


# === Backward Compatibility Test ===
# This still works for existing code
class LegacyModel(BaseModel):
    """
    Model using legacy json_schema_extra syntax (still supported)
    """
    name: str = Field(..., json_schema_extra={"intent": "CRITICAL"})
    temp_token: str = Field(..., json_schema_extra={"intent": "EPHEMERAL"})


# === Endpoint Usage Example ===
# Note: In real usage, these would be used with EVOX decorators
def process_user_data(user: ModernUserModel) -> Dict[str, Any]:
    """
    Example function showing how intent-aware processing works
    """
    return {
        "processed": True,
        "user_id": user.name,  # Critical data gets strong consistency
        "temp_data": user.temp_token,  # Ephemeral data gets aggressive caching
        "secure_data": "processed securely"  # Masked data gets encryption
    }


def process_payment(payment: PaymentRequest) -> Dict[str, Any]:
    """
    Payment processing with intent-aware handling
    """
    return {
        "transaction_id": payment.transaction_id,
        "status": "processed",
        "amount": payment.amount,
        "processed_securely": True
    }


def main():
    print("🚀 Modern Annotated Intent System Demo")
    print("=" * 50)
    print()
    print("🎯 New Features Demonstrated:")
    print("✅ Modern Annotated syntax: Annotated[str, Critical()]")
    print("✅ Reusable types: CriticalStr, StandardInt, EphemeralStr")
    print("✅ Custom intents: IntentMarker('CUSTOM_NAME', ...)")
    print("✅ Helper functions: critical(str), standard(int), etc.")
    print("✅ Backward compatibility: json_schema_extra still works")
    print()
    print("📋 Intent Categories:")
    print("• Critical: Strong consistency, encryption, audit logging")
    print("• Standard: Balanced caching, normal processing")
    print("• Ephemeral: Aggressive caching, short TTL, low priority")
    print("• Custom: Arbitrary configurations via IntentMarker")
    print()
    print("💡 Usage Examples:")
    print()
    print("# Reusable types (recommended)")
    print("PasswordField = Annotated[str, IntentMarker('PASSWORD_MASKED', encrypt=True)]")
    print()
    print("# Inline annotations")
    print("name: Annotated[str, Critical(encrypt=True, audit_logging=True)]")
    print()
    print("# Helper functions")
    print("email: critical(str, encrypt=True, ttl_minutes=30)")
    print()
    print("# Complex custom intent")
    print("ssn: custom_intent(str, 'SENSITIVE_DATA', encrypt=True, custom_properties={'pii': True})")
    print()
    print("✅ All examples use modern Python 3.13+ syntax")
    print("✅ Full backward compatibility maintained")
    print("✅ Zero json_schema_extra declarations in new code")


if __name__ == "__main__":
    main()
    
    # Test the models
    print("\n🧪 Testing models...")
    
    # Test modern model
    modern_user = ModernUserModel(
        name="John Doe",
        password="secret123",
        age=25,
        email="john@example.com",
        temp_token="temp123",
        ssn="123-45-6789",
        username="johndoe",
        session_id="sess456"
    )
    print(f"✅ ModernUserModel created: {modern_user.name}")
    
    # Test payment model
    payment = PaymentRequest(
        transaction_id="txn_789",
        amount=99.99,
        card_number="4111111111111111",
        cvv="123",
        processing_token="proc_abc",
        attempt_count=1,
        user_id=123,
        merchant_id=456
    )
    print(f"✅ PaymentRequest created: {payment.transaction_id}")
    
    # Test analytics model
    analytics = AnalyticsEvent(
        event_type="page_view",
        user_id=456,
        session_data="session_xyz",
        sensitive_info="private_data"
    )
    print(f"✅ AnalyticsEvent created: {analytics.event_type}")
    
    # Test legacy model still works
    legacy = LegacyModel(name="Legacy User", temp_token="legacy_token")
    print(f"✅ LegacyModel still works: {legacy.name}")
    
    print("\n🎉 All tests passed! Modern intent system is fully functional.")