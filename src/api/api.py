#!/usr/bin/env python3
"""
Vedic Numerology-Astrology REST API
====================================

FastAPI-based REST API for numerology and astrology calculations.
Provides endpoints for real-time calculations and data retrieval.
"""

import os
import sys
from datetime import datetime, date, time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from vedic_astrology_core import VedicAstrologyChart, create_birth_chart
    from vedic_astrology_core.astrology import AyanamsaSystem
    from vedic_astrology_core.config import Planet
    from vedic_astrology_core.time_series import (
        TimeSeriesConfig,
        compute_astrology_strength_series,
        compute_combined_series,
        compute_numerology_series,
    )
    from vedic_numerology.numerology import calculate_complete_numerology
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    import json
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Please ensure the package is properly installed.")
    sys.exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="Vedic Numerology-Astrology API",
    description="REST API for Vedic numerology and astrology calculations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class BirthData(BaseModel):
    """Birth data input model."""
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format", example="1984-08-27")
    birth_time: Optional[str] = Field("12:00", description="Birth time in HH:MM format", example="10:30")
    latitude: float = Field(28.6139, description="Birth latitude in decimal degrees", example=28.6139)
    longitude: float = Field(77.1025, description="Birth longitude in decimal degrees", example=77.1025)
    timezone: str = Field("Asia/Kolkata", description="Timezone string", example="Asia/Kolkata")
    ayanamsa_system: str = Field("lahiri", description="Ayanamsa system (lahiri/raman)", example="lahiri")

    @validator('birth_date')
    def validate_birth_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Birth date must be in YYYY-MM-DD format')

    @validator('birth_time')
    def validate_birth_time(cls, v):
        if v:
            try:
                datetime.strptime(v, '%H:%M')
                return v
            except ValueError:
                raise ValueError('Birth time must be in HH:MM format')
        return v

class NumerologyResponse(BaseModel):
    """Numerology calculation response."""
    mulanka: Dict[str, Any]
    bhagyanka: Dict[str, Any]
    timestamp: str

class AstrologyResponse(BaseModel):
    """Astrology calculation response."""
    planets: Dict[str, Any]
    ascendant: Dict[str, Any]
    houses: List[Dict[str, Any]]
    ayanamsa: float
    timestamp: str

class AnalysisResponse(BaseModel):
    """Complete analysis response."""
    numerology: Dict[str, Any]
    astrology: Dict[str, Any]
    support_analysis: Dict[str, Any]
    timestamp: str

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "🪐 Vedic Numerology-Astrology API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "numerology": "/api/v1/numerology",
            "astrology": "/api/v1/astrology",
            "analysis": "/api/v1/analysis",
            "planets": "/api/v1/planets",
            "planet_strength_series": "/api/v1/planet-strength-series",
            "numerology_series": "/api/v1/numerology-series",
            "combined_series": "/api/v1/combined-series",
            "health": "/api/v1/health"
        }
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/v1/numerology", response_model=NumerologyResponse)
async def calculate_numerology(birth_data: BirthData):
    """Calculate numerology for given birth data."""
    try:
        # Parse birth date and time
        from datetime import datetime
        birth_date = datetime.strptime(birth_data.birth_date, "%Y-%m-%d").date()
        birth_time = datetime.strptime(birth_data.birth_time, "%H:%M:%S").time() if birth_data.birth_time else None

        # Calculate numerology using use case module
        numerology_data = calculate_complete_numerology(
            birth_date, birth_time, birth_data.latitude, birth_data.longitude
        )

        return NumerologyResponse(
            mulanka=numerology_data["mulanka"],
            bhagyanka=numerology_data["bhagyanka"],
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")

@app.post("/api/v1/astrology", response_model=AstrologyResponse)
async def calculate_astrology(birth_data: BirthData):
    """Calculate astrology for given birth data."""
    try:
        # Create analysis object
        chart = VedicAstrologyChart(
            birth_date=birth_data.birth_date,
            birth_time=birth_data.birth_time,
            latitude=birth_data.latitude,
            longitude=birth_data.longitude,
            timezone=birth_data.timezone,
            ayanamsa_system=birth_data.ayanamsa_system.upper()
        )

        birth_chart = chart.chart

        # Format planetary data
        planets = {}
        for planet_name, planet_data in birth_chart.planets.items():
            planets[planet_name] = {
                "longitude": planet_data.longitude,
                "latitude": planet_data.latitude,
                "sign": planet_data.sign.name,
                "degrees_in_sign": planet_data.degrees_in_sign,
                "retrograde": getattr(planet_data, 'retrograde', False)
            }

        # Format house data
        houses = []
        for i, house_data in enumerate(chart.houses):
            houses.append({
                "house": i + 1,
                "longitude": house_data.longitude,
                "sign": house_data.sign_name,
                "degrees_in_sign": house_data.degrees_in_sign
            })

        return AstrologyResponse(
            planets=planets,
            ascendant={
                "longitude": birth_chart.ascendant.longitude,
                "sign": birth_chart.ascendant.sign_name,
                "degrees_in_sign": birth_chart.ascendant.degrees_in_sign
            },
            houses=houses,
            ayanamsa=birth_chart.ayanamsa,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")

@app.post("/api/v1/analysis", response_model=AnalysisResponse)
async def complete_analysis(birth_data: BirthData):
    """Perform complete numerology-astrology analysis."""
    try:
        # Parse birth data
        from datetime import datetime
        birth_date = datetime.strptime(birth_data.birth_date, "%Y-%m-%d").date()
        birth_time = datetime.strptime(birth_data.birth_time, "%H:%M:%S").time() if birth_data.birth_time else None

        # Get numerology data
        numerology_data = calculate_complete_numerology(
            birth_date, birth_time, birth_data.latitude, birth_data.longitude
        )

        # Create astrology chart
        chart_obj = VedicAstrologyChart(
            birth_date=birth_data.birth_date,
            birth_time=birth_data.birth_time,
            latitude=birth_data.latitude,
            longitude=birth_data.longitude,
            timezone=birth_data.timezone,
            ayanamsa_system=birth_data.ayanamsa_system.upper()
        )

        # Get astrology chart
        birth_chart = chart_obj.chart

        # Calculate support analysis (this would need to be implemented in numerology use case)
        # For now, provide basic structure
        support_analysis = {
            "mulanka": {"planet": numerology_data["mulanka"]["planet"], "support_level": "Analysis pending"},
            "bhagyanka": {"planet": numerology_data["bhagyanka"]["planet"], "support_level": "Analysis pending"},
            "overall": {"harmony_level": "Analysis pending"}
        }
        astrology = {
            "ayanamsa": birth_chart.ayanamsa,
            "ascendant": {
                "sign": birth_chart.ascendant.sign_name,
                "degrees_in_sign": birth_chart.ascendant.degrees_in_sign
            },
            "planets": {
                planet_name: {
                    "sign": planet_data.sign.name,
                    "degrees_in_sign": planet_data.degrees_in_sign
                }
                for planet_name, planet_data in birth_chart.planets.items()
            }
        }

        return AnalysisResponse(
            numerology={
                "mulanka": numerology_data["mulanka"],
                "bhagyanka": numerology_data["bhagyanka"]
            },
            astrology=astrology,
            support_analysis=support_analysis,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis error: {str(e)}")

@app.get("/api/v1/planets")
async def get_planets():
    """Get information about all planets."""
    planets_info = {}
    for planet in Planet:
        planets_info[planet.name] = {
            "number": planet.value,
            "rulership": getattr(planet, 'rulership', 'Unknown'),
            "element": getattr(planet, 'element', 'Unknown'),
            "description": getattr(planet, 'description', 'Unknown')
        }

    return {
        "planets": planets_info,
        "total": len(planets_info),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/examples")
async def get_examples():
    """Get example API usage."""
    return {
        "examples": {
            "numerology_calculation": {
                "endpoint": "POST /api/v1/numerology",
                "payload": {
                    "birth_date": "1984-08-27",
                    "birth_time": "10:30",
                    "latitude": 28.6139,
                    "longitude": 77.1025
                }
            },
            "complete_analysis": {
                "endpoint": "POST /api/v1/analysis",
                "payload": {
                    "birth_date": "1990-05-15",
                    "birth_time": "14:20",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "ayanamsa_system": "raman"
                }
            },
            "curl_example": """curl -X POST "http://localhost:8000/api/v1/analysis" \\
  -H "Content-Type: application/json" \\
  -d '{
    "birth_date": "1984-08-27",
    "birth_time": "10:30",
    "latitude": 28.6139,
    "longitude": 77.1025
  }'"""
        }
    }


def _parse_planets(planets: Optional[str]) -> Optional[List[Planet]]:
    if not planets:
        return None
    items = [p.strip().upper() for p in planets.split(",") if p.strip()]
    parsed: List[Planet] = []
    for item in items:
        try:
            parsed.append(Planet[item])
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown planet '{item}'. Expected one of: {[p.name for p in Planet]}",
            )
    return parsed


@app.get("/api/v1/planet-strength-series")
async def planet_strength_series(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    step_days: int = Query(1, ge=1, le=366, description="Step size in days"),
    planets: Optional[str] = Query(
        None, description="Comma-separated planet names (e.g., MARS,VENUS). Defaults to all."
    ),
    latitude: float = Query(28.6139, description="Latitude for astrology calculation"),
    longitude: float = Query(77.1025, description="Longitude for astrology calculation"),
):
    """Astrology dignity strength over time."""
    planet_list = _parse_planets(planets)
    cfg = TimeSeriesConfig(latitude=latitude, longitude=longitude)
    df = compute_astrology_strength_series(
        start_date=start, end_date=end, step_days=step_days, planets=planet_list, config=cfg
    )
    return {"start": start, "end": end, "step_days": step_days, "data": df.to_dict(orient="list")}


@app.get("/api/v1/numerology-series")
async def numerology_series(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    step_days: int = Query(1, ge=1, le=366, description="Step size in days"),
    planets: Optional[str] = Query(
        None, description="Comma-separated planet names (e.g., MARS,VENUS). Defaults to all."
    ),
):
    """Numerology (Mulanka active planet strength) over time."""
    planet_list = _parse_planets(planets)
    df = compute_numerology_series(
        start_date=start, end_date=end, step_days=step_days, planets=planet_list
    )
    return {"start": start, "end": end, "step_days": step_days, "data": df.to_dict(orient="list")}


@app.get("/api/v1/combined-series")
async def combined_series(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    step_days: int = Query(1, ge=1, le=366, description="Step size in days"),
    planets: Optional[str] = Query(
        None, description="Comma-separated planet names (e.g., MARS,VENUS). Defaults to all."
    ),
    latitude: float = Query(28.6139, description="Latitude for astrology calculation"),
    longitude: float = Query(77.1025, description="Longitude for astrology calculation"),
):
    """Combined numerology + astrology time-series over time."""
    planet_list = _parse_planets(planets)
    cfg = TimeSeriesConfig(latitude=latitude, longitude=longitude)
    df = compute_combined_series(
        start_date=start, end_date=end, step_days=step_days, planets=planet_list, config=cfg
    )
    return {"start": start, "end": end, "step_days": step_days, "data": df.to_dict(orient="list")}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # It's a good practice to log the exception with its traceback
    import traceback
    import logging

    # Log the full exception details with traceback
    logging.exception(f"Unhandled exception in request to {request.url}: {exc}")

    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status_code": 500,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
        log_level="info"
    )