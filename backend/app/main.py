from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.database import engine, SessionLocal
from app.db.models import Base
from app.db.seed import seed_data
from app.api import auth, dashboard, invoices, fraud, forecast, budget, vendor, cfo, simulator

app = FastAPI(
    title="Centura AI - Enterprise Financial Intelligence Platform",
    description="Autonomous AI-powered CFO and Financial Intelligence System",
    version="1.0.0",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Create tables and seed database schema."""
    Base.metadata.create_all(bind=engine)

# Mount primary API routes with alias routes to prevent 404 errors
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

# Invoice endpoints (both plural and singular)
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["Invoice Intelligence"])
app.include_router(invoices.router, prefix="/api/v1/invoice", tags=["Invoice Intelligence Alias"])

# Fraud endpoints (both plural and singular)
app.include_router(fraud.router, prefix="/api/v1/fraud", tags=["Fraud Detection"])
app.include_router(fraud.router, prefix="/api/v1/frauds", tags=["Fraud Detection Alias"])

# Forecast endpoints (both plural and singular)
app.include_router(forecast.router, prefix="/api/v1/forecast", tags=["Cash Flow Forecast"])
app.include_router(forecast.router, prefix="/api/v1/forecasts", tags=["Cash Flow Forecast Alias"])

# Budget endpoints (both plural and singular)
app.include_router(budget.router, prefix="/api/v1/budget", tags=["Budget Optimization"])
app.include_router(budget.router, prefix="/api/v1/budgets", tags=["Budget Optimization Alias"])

# Vendor endpoints (both plural and singular)
app.include_router(vendor.router, prefix="/api/v1/vendor", tags=["Vendor Risk"])
app.include_router(vendor.router, prefix="/api/v1/vendors", tags=["Vendor Risk Alias"])

# CFO Agent & Simulator endpoints
app.include_router(cfo.router, prefix="/api/v1/cfo", tags=["AI CFO Agent"])
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulator & Digital Twin"])
app.include_router(simulator.router, prefix="/api/v1/workflow", tags=["Workflow Center Alias"])

@app.get("/")
def root():
    return {
        "platform": "Centura AI",
        "version": "1.0.0",
        "status": "operational",
        "modules": ["Invoice Intelligence", "Fraud Detection", "Cash Flow Forecasting",
                    "Budget Optimization", "Vendor Risk", "AI CFO Agent", "What-If Simulator", "Digital Twin"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "Centura AI Backend"}
