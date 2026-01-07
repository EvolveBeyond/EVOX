"""
EVOX Intent System Deep Dive
============================

This example focuses specifically on EVOX's powerful intent system:
- Data Intents: Field-level processing rules (EPHEMERAL, STANDARD, CRITICAL, SENSITIVE)
- Operation Intents: Endpoint categorization and behavior (user_management, analytics, payment)
- Custom Intents: Creating your own intent types with custom configurations
- Intent Processing: How intents affect caching, encryption, consistency, and routing

This showcases one of EVOX's most distinctive features.
"""

from evoid import (
    service, get, post, put, delete, Body, Param,
    Controller, GET, POST, PUT, DELETE
)
from evoid.core.data.intents.data_intents import (
    BuiltInDataIntent, CustomIntentConfig, register_custom_data_intent
)
from evoid.core.data.intents.operation_intents import (
    user_management, analytics, payment, system_admin
)
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Annotated
from datetime import datetime
from evoid.core.data.intents.annotated_intents import Critical, Standard, Ephemeral, custom_intent
import uuid


# === CUSTOM INTENT REGISTRATION ===

# Register a custom intent for financial data
financial_data_config = CustomIntentConfig(
    intent_name="FINANCIAL_DATA",
    encrypt=True,
    audit_logging=True,
    strong_consistency=True,
    cache_enabled=False,
    replication_required=True,
    task_priority="high",
    emergency_buffer=True,
    custom_properties={
        "regulatory_compliance": True,
        "pci_dss": True,
        "retention_days": 365
    }
)
register_custom_data_intent("FINANCIAL_DATA", financial_data_config)

# Register intent for personally identifiable information
pii_config = CustomIntentConfig(
    intent_name="PII_DATA",
    encrypt=True,
    audit_logging=True,
    cache_enabled=False,
    custom_properties={
        "gdpr_compliant": True,
        "mask_in_logs": True,
        "requires_consent": True
    }
)
register_custom_data_intent("PII_DATA", pii_config)


# === DATA MODELS WITH VARIOUS INTENT TYPES ===

class CustomerProfile(BaseModel):
    """Customer profile demonstrating modern intent annotations"""
    
    # Standard identifier - cached, normal processing
    customer_id: Annotated[str, Standard()] = str(uuid.uuid4())
    
    # PII data - encrypted, audited, not cached
    email: Annotated[str, custom_intent("PII_DATA", encrypt=True, audit_logging=True, cache_enabled=False)]
    
    # Standard data - normal processing
    first_name: Annotated[str, Standard()]
    last_name: Annotated[str, Standard()]
    
    # Financial data - highly protected, strong consistency
    credit_card_last_four: Annotated[str, custom_intent("FINANCIAL_DATA", encrypt=True, audit_logging=True, strong_consistency=True, replication_required=True)]
    
    # Ephemeral data - cache-friendly, short retention
    session_token: Optional[Annotated[str, Ephemeral(ttl_minutes=10)]] = None
    
    # Critical data - strong consistency, replicated
    account_status: Annotated[str, Critical(replication_required=True)] = "active"


class TransactionRecord(BaseModel):
    """Transaction model with modern intent annotations"""
    
    transaction_id: Annotated[str, Critical(replication_required=True, backup_required=True)] = f"txn_{uuid.uuid4().hex[:12]}"
    customer_id: Annotated[str, Standard()]
    amount: Annotated[float, custom_intent("FINANCIAL_DATA", encrypt=True, audit_logging=True, strong_consistency=True)]
    currency: Annotated[str, Standard()] = "USD"
    timestamp: Annotated[datetime, Ephemeral(ttl_minutes=30)] = datetime.now()
    
    # Custom intent with inline configuration
    merchant_data: Annotated[Dict[str, Any], custom_intent(
        "MERCHANT_INFO", 
        encrypt=False, 
        audit_logging=True, 
        cache_enabled=True, 
        ttl_minutes=1440,  # 24 hours
        trusted_source=True
    )] = {}


# === OPERATION INTENT ENDPOINTS ===

# User Management Operations
@user_management(priority="high", auth_required=True)
@Controller("/api/users", tags=["user-management"])
class UserManagementController:
    
    @GET("/{user_id}")
    async def get_user(self, user_id: str = Param(str)) -> CustomerProfile:
        """High-priority user retrieval"""
        return CustomerProfile(
            customer_id=user_id,
            email=f"user{user_id}@example.com",
            first_name="John",
            last_name="Doe",
            credit_card_last_four="1234",
            account_status="active"
        )
    
    @POST("/")
    async def create_user(self, profile: CustomerProfile = Body(...)) -> Dict[str, Any]:
        """Create new user with full intent processing"""
        return {
            "customer_id": profile.customer_id,
            "status": "created",
            "intents_processed": [
                "PII_DATA (email)",
                "FINANCIAL_DATA (credit_card)",
                "CRITICAL (account_status)"
            ]
        }


# Analytics Operations  
@analytics(sample_rate=0.1, priority="low")
@get("/analytics/metrics")
async def get_analytics_metrics(timeframe: str = Param("24h")) -> Dict[str, Any]:
    """Low-priority analytics with sampling"""
    return {
        "timeframe": timeframe,
        "metrics": {
            "active_users": 1250,
            "conversion_rate": 0.032,
            "avg_session": "12m 45s"
        },
        "sample_rate_applied": True,
        "priority": "low"
    }


# Payment Operations
@payment(priority="highest", tracing_enabled=True, auth_required=True)
@post("/payments/charge")
async def process_payment(transaction: TransactionRecord = Body(...)) -> Dict[str, Any]:
    """Highest priority payment processing with full tracing"""
    return {
        "transaction_id": transaction.transaction_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "status": "processed",
        "security": {
            "encryption_applied": True,
            "audit_logged": True,
            "tracing_enabled": True
        }
    }


# System Administration
@system_admin(priority="critical", auth_required=True)
@delete("/admin/users/{user_id}")
async def delete_user(user_id: str = Param(str)) -> Dict[str, Any]:
    """Critical admin operation requiring highest privileges"""
    return {
        "user_id": user_id,
        "action": "deleted",
        "priority": "critical",
        "requires_approval": True
    }


# === INTENT INSPECTION ENDPOINT ===

@get("/debug/intents")
async def inspect_intents() -> Dict[str, Any]:
    """Debug endpoint showing how intents are processed"""
    from evoid.core.data.intents.intent_system import get_intent_registry
    
    registry = get_intent_registry()
    
    return {
        "registered_data_intents": list(registry._data_intents.keys()),
        "built_in_intents": [intent.value for intent in BuiltInDataIntent],
        "custom_configs": {
            "FINANCIAL_DATA": financial_data_config.__dict__,
            "PII_DATA": pii_config.__dict__
        },
        "processing_rules": {
            "EPHEMERAL": "Cache-friendly, short retention",
            "STANDARD": "Normal processing",
            "CRITICAL": "Strong consistency, replicated",
            "SENSITIVE": "Encrypted storage",
            "CUSTOM": "Per-intent configuration rules"
        }
    }


# === MAIN APPLICATION ===

app = service("intent-system-demo").port(8000).build()


if __name__ == "__main__":
    print("🧠 EVOX Intent System Deep Dive")
    print("=" * 35)
    print()
    print("Intent Types Demonstrated:")
    print("📊 Built-in Data Intents:")
    print("   • EPHEMERAL    - Cache-friendly, temporary data")
    print("   • STANDARD     - Normal processing")
    print("   • CRITICAL     - Strong consistency, replicated")
    print("   • SENSITIVE    - Encrypted storage")
    print()
    print("⚙️  Operation Intents:")
    print("   • user_management  - High priority user operations")
    print("   • analytics        - Low priority with sampling")
    print("   • payment          - Highest priority with tracing")
    print("   • system_admin     - Critical administrative tasks")
    print()
    print("✨ Custom Intents Created:")
    print("   • FINANCIAL_DATA   - PCI-DSS compliant financial data")
    print("   • PII_DATA         - GDPR-compliant personal data")
    print()
    print("Endpoints Available:")
    print("  GET    /api/users/{user_id}           (user_management)")
    print("  POST   /api/users/                    (user_management)")
    print("  GET    /analytics/metrics             (analytics)")
    print("  POST   /payments/charge               (payment)")
    print("  DELETE /admin/users/{user_id}         (system_admin)")
    print("  GET    /debug/intents                 (introspection)")
    print()
    print("To run: python 03_intent_system.py")
    
    # Uncomment to run:
    # app.run(dev=True)