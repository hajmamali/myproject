#!/usr/bin/env python3
"""
MAHOUN Governance Kernel - Standalone Runtime
Purpose: Pure governance validation and enforcement
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
import uvicorn
from prometheus_client import Counter, Histogram, generate_latest
from loguru import logger

# Configure logging
logger.configure(
    handlers=[
        {
            "sink": sys.stdout,
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            "level": "INFO"
        }
    ]
)

# Metrics
governance_requests = Counter('governance_requests_total', 'Total governance requests', ['operation', 'result'])
governance_duration = Histogram('governance_duration_seconds', 'Governance operation duration', ['operation'])

class GovernanceRequest(BaseModel):
    query_type: str
    correlation_id: str
    actor_id: str
    resource_id: str = None
    metadata: Dict[str, Any] = {}

class GovernanceResponse(BaseModel):
    allowed: bool
    reason: str
    correlation_id: str
    validation_id: str
    metadata: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("🔒 MAHOUN Governance Kernel starting...")
    
    # Validate environment
    if os.getenv("MAHOUN_ENV") != "production":
        logger.warning("⚠️ Not running in production mode")
    
    # Initialize governance components
    from mahoun.core.governance_kernel.kernel import GovernanceKernel
    app.state.kernel = GovernanceKernel()
    
    logger.success("✅ Governance Kernel initialized")
    yield
    
    logger.info("🔒 Governance Kernel shutting down")

# Create FastAPI app
app = FastAPI(
    title="MAHOUN Governance Kernel",
    description="Pure governance validation and enforcement service",
    version="1.0.0",
    docs_url="/docs" if os.getenv("MAHOUN_ENV") != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if os.getenv("MAHOUN_ENV") != "production" else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "governance-kernel", "*.mahoun.internal"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://api-server:8000"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "governance-kernel"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(generate_latest(), media_type="text/plain")

@app.post("/v1/governance/enforce", response_model=GovernanceResponse)
async def enforce_governance(request: GovernanceRequest):
    """Core governance enforcement endpoint"""
    with governance_duration.labels(operation="enforce").time():
        try:
            # Get kernel from app state
            kernel = app.state.kernel
            
            # Perform governance validation
            result = await kernel.validate_request(
                query_type=request.query_type,
                correlation_id=request.correlation_id,
                actor_id=request.actor_id,
                resource_id=request.resource_id,
                metadata=request.metadata
            )
            
            governance_requests.labels(
                operation="enforce", 
                result="allowed" if result.allowed else "denied"
            ).inc()
            
            return result
            
        except Exception as e:
            logger.error(f"Governance validation failed: {e}")
            governance_requests.labels(operation="enforce", result="error").inc()
            raise HTTPException(status_code=500, detail="Governance validation failed")

@app.get("/v1/governance/status")
async def governance_status():
    """Get governance kernel status"""
    kernel = app.state.kernel
    return {
        "status": "active",
        "version": "1.0.0",
        "uptime": kernel.get_uptime(),
        "stats": kernel.get_stats()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        workers=1,
        loop="uvloop",
        http="httptools",
        log_level="info",
        access_log=False
    )