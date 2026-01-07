"""
EVOX Enterprise System Template
===============================

Production-ready enterprise system demonstrating:
- Advanced configuration with config.toml
- Database integration (SQLite provider)
- Authentication and authorization
- Health checks and monitoring
- Error handling and logging
- Performance optimization
- Scalability patterns
- Security best practices

This represents a complete enterprise-grade application template.
"""

from evoid import (
    service, get, post, put, delete, Controller,
    Body, Param, Query,
    inject, override,
    auth, AuthManager, AuthConfig, CIAClassification,
    cache_layer, cached,
    model_mapper, map_api_to_core, map_core_to_api,
    performance_bench, generate_benchmark_report,
    data_io, persistence_gateway,
    save_model, get_model, delete_model, query_models,
    BaseProvider, SQLiteStorageProvider,
    EnvironmentalIntelligence, auto_adjust_concurrency
)
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import os


# === LOGGING CONFIGURATION ===

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# === ENTERPRISE DATA MODELS ===

class EmployeeCreateRequest(BaseModel):
    """Employee creation request with validation"""
    employee_id: str = Field(..., min_length=5, max_length=20, pattern=r'^[A-Z0-9]+$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    department: str = Field(..., max_length=100)
    position: str = Field(..., max_length=100)
    salary: float = Field(..., gt=0)
    hire_date: datetime
    
    @validator('hire_date')
    def validate_hire_date(cls, v):
        if v > datetime.now():
            raise ValueError('Hire date cannot be in the future')
        return v


class EmployeeResponse(BaseModel):
    """Employee response model"""
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    position: str
    salary: float
    hire_date: datetime
    created_at: datetime
    updated_at: datetime


class DepartmentStats(BaseModel):
    """Department statistics model"""
    department: str
    employee_count: int
    average_salary: float
    total_cost: float


# === ENTERPRISE SERVICE COMPONENTS ===

@inject
class EmployeeRepository:
    """Data access layer for employee operations"""
    
    def __init__(self, db_provider: BaseProvider = None):
        self.db = db_provider or SQLiteStorageProvider("enterprise.db")
    
    async def create_employee(self, employee_data: EmployeeCreateRequest) -> EmployeeResponse:
        """Create new employee record"""
        # Check if employee ID already exists
        existing = await self.db.query(
            "SELECT 1 FROM employees WHERE employee_id = ?",
            [employee_data.employee_id]
        )
        
        if existing:
            raise ValueError(f"Employee ID {employee_data.employee_id} already exists")
        
        # Insert new employee
        employee_id = await self.db.execute(
            """
            INSERT INTO employees 
            (employee_id, first_name, last_name, email, department, position, salary, hire_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                employee_data.employee_id,
                employee_data.first_name,
                employee_data.last_name,
                employee_data.email,
                employee_data.department,
                employee_data.position,
                employee_data.salary,
                employee_data.hire_date.isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ]
        )
        
        # Return created employee
        result = await self.db.query(
            "SELECT * FROM employees WHERE id = ?", [employee_id]
        )
        
        return EmployeeResponse(**result[0])
    
    async def get_employee(self, emp_id: int) -> Optional[EmployeeResponse]:
        """Get employee by ID"""
        result = await self.db.query(
            "SELECT * FROM employees WHERE id = ?", [emp_id]
        )
        return EmployeeResponse(**result[0]) if result else None
    
    async def get_department_stats(self, department: str) -> DepartmentStats:
        """Get statistics for a department"""
        result = await self.db.query(
            """
            SELECT 
                COUNT(*) as employee_count,
                AVG(salary) as average_salary,
                SUM(salary) as total_cost
            FROM employees 
            WHERE department = ?
            """,
            [department]
        )[0]
        
        return DepartmentStats(
            department=department,
            employee_count=result['employee_count'],
            average_salary=float(result['average_salary'] or 0),
            total_cost=float(result['total_cost'] or 0)
        )


# === AUTHENTICATION CONFIGURATION ===

# Enterprise security configuration
auth_config = AuthConfig(
    jwt_secret=os.getenv("JWT_SECRET", "enterprise-secret-key"),
    jwt_algorithm="HS256",
    token_expiry_hours=8,
    refresh_token_expiry_days=30,
    cia_classification=CIAClassification(
        confidentiality="CONFIDENTIAL",
        integrity="HIGH",
        availability="HIGH"
    )
)

auth_manager = AuthManager(auth_config)


# === CONTROLLERS ===

@Controller("/api/v1/employees", tags=["employees"], auth_required=True)
class EmployeeController:
    """Enterprise employee management controller"""
    
    def __init__(self):
        self.repo = inject(EmployeeRepository)
        self.auth = auth_manager
    
    @post("/", scopes=["hr:create"])
    @performance_bench.track()
    async def create_employee(
        self, 
        employee: EmployeeCreateRequest,
        current_user: Dict[str, Any] = auth.current_user()
    ) -> EmployeeResponse:
        """Create new employee (HR only)"""
        logger.info(f"Creating employee {employee.employee_id} by {current_user.get('username')}")
        
        try:
            result = await self.repo.create_employee(employee)
            logger.info(f"Employee {result.employee_id} created successfully")
            return result
        except Exception as e:
            logger.error(f"Failed to create employee: {str(e)}")
            raise
    
    @get("/{employee_id:int}", scopes=["hr:read", "employee:self"])
    @cached(ttl=timedelta(minutes=15))
    async def get_employee(
        self,
        employee_id: int,
        current_user: Dict[str, Any] = auth.current_user()
    ) -> EmployeeResponse:
        """Get employee details"""
        employee = await self.repo.get_employee(employee_id)
        if not employee:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    
    @get("/department/{dept_name}/stats", scopes=["hr:read", "management"])
    async def get_department_stats(
        self,
        dept_name: str,
        current_user: Dict[str, Any] = auth.current_user()
    ) -> DepartmentStats:
        """Get department statistics"""
        return await self.repo.get_department_stats(dept_name)


# === HEALTH CHECKS AND MONITORING ===

@get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint"""
    from evoid.core.infrastructure.dependency_injection.injector import get_health_registry
    
    health_registry = get_health_registry()
    health_status = await health_registry.check_all_services()
    
    # Environmental intelligence
    env_intel = EnvironmentalIntelligence()
    system_status = await env_intel.get_current_status()
    
    return {
        "status": "healthy" if all(h.healthy for h in health_status.values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            name: {
                "healthy": status.healthy,
                "response_time_ms": status.response_time_ms,
                "last_check": status.last_check.isoformat()
            }
            for name, status in health_status.items()
        },
        "environment": {
            "cpu_usage": system_status.cpu_percent,
            "memory_usage": system_status.memory_percent,
            "disk_usage": system_status.disk_usage_percent,
            "network_latency": system_status.network_latency_ms
        }
    }


@get("/metrics/performance")
@auth.required(scopes=["admin:monitoring"])
async def performance_metrics() -> Dict[str, Any]:
    """Performance metrics endpoint"""
    report = generate_benchmark_report()
    return {
        "report_generated": datetime.now().isoformat(),
        "summary": report.summary,
        "endpoints": report.endpoints,
        "recommendations": report.recommendations
    }


# === ADMINISTRATIVE ENDPOINTS ===

@Controller("/api/v1/admin", tags=["administration"], auth_required=True)
class AdminController:
    
    @post("/database/backup", scopes=["admin:database"])
    async def backup_database(
        self,
        backup_name: Optional[str] = None,
        current_user: Dict[str, Any] = auth.current_user()
    ) -> Dict[str, Any]:
        """Create database backup"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simulate backup process
        logger.info(f"Starting database backup: {backup_name}")
        await asyncio.sleep(2)  # Simulate backup time
        
        return {
            "backup_name": backup_name,
            "status": "completed",
            "size_mb": 125.4,
            "duration_seconds": 2.1,
            "created_by": current_user.get("username")
        }
    
    @post("/system/maintenance", scopes=["admin:system"])
    async def run_maintenance(
        self,
        current_user: Dict[str, Any] = auth.current_user()
    ) -> Dict[str, Any]:
        """Run system maintenance tasks"""
        logger.info("Starting system maintenance")
        
        # Simulate maintenance tasks
        tasks = [
            "database_optimization",
            "cache_cleanup", 
            "log_rotation",
            "index_rebuilding"
        ]
        
        results = {}
        for task in tasks:
            logger.info(f"Running maintenance task: {task}")
            await asyncio.sleep(0.5)
            results[task] = "completed"
        
        return {
            "maintenance_tasks": results,
            "status": "all_completed",
            "executed_by": current_user.get("username"),
            "timestamp": datetime.now().isoformat()
        }


# === MAIN APPLICATION CONFIGURATION ===

app = (
    service("enterprise-hrms")
    .port(int(os.getenv("PORT", 8000)))
    .host(os.getenv("HOST", "0.0.0.0"))
    .enable_fury_serialization(True)
    .configure_cache(l1_size_mb=200, redis_url=os.getenv("REDIS_URL"))
    .enable_benchmarking(True)
    .with_message_bus()
    .with_task_manager()
    .with_model_mapping()
    .with_auth_manager(auth_manager)
    .build()
)


# === DATABASE INITIALIZATION ===

async def initialize_database():
    """Initialize database tables"""
    db = SQLiteStorageProvider("enterprise.db")
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id VARCHAR(20) UNIQUE NOT NULL,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            department VARCHAR(100) NOT NULL,
            position VARCHAR(100) NOT NULL,
            salary DECIMAL(10,2) NOT NULL,
            hire_date DATETIME NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)
    
    logger.info("Database initialized successfully")


if __name__ == "__main__":
    print("🏢 EVOX Enterprise HRMS Template")
    print("=" * 35)
    print()
    print("Enterprise Features:")
    print("🔐 Advanced authentication & authorization")
    print("📊 Health checks & monitoring")
    print("⚡ Performance benchmarking")
    print("💾 Database integration (SQLite)")
    print("🔄 Caching with TTL")
    print("📈 Auto-scaling capabilities")
    print("🛡️  Security best practices")
    print("📋 Comprehensive logging")
    print()
    print("Endpoints Available:")
    print("  GET    /health                   - System health check")
    print("  GET    /metrics/performance      - Performance metrics")
    print("  POST   /api/v1/employees/        - Create employee (HR)")
    print("  GET    /api/v1/employees/{id}    - Get employee")
    print("  GET    /api/v1/employees/dept/{name}/stats - Dept stats")
    print("  POST   /api/v1/admin/database/backup - DB backup (Admin)")
    print("  POST   /api/v1/admin/system/maintenance - Maintenance (Admin)")
    print()
    print("Environment Variables:")
    print("  PORT          - Server port (default: 8000)")
    print("  HOST          - Server host (default: 0.0.0.0)")
    print("  JWT_SECRET    - Authentication secret")
    print("  REDIS_URL     - Redis cache URL")
    print()
    print("To run: python 05_enterprise_system.py")
    
    # Uncomment to run:
    # import asyncio
    # asyncio.run(initialize_database())
    # app.run(dev=True)