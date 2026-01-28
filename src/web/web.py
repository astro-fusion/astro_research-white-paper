#!/usr/bin/env python3
"""
Vedic Numerology-Astrology Web Interface
=======================================

Flask-based web interface for the Vedic Numerology-Astrology system.
Provides interactive timeline visualization of planetary strength and numerology.
"""

import os
import sys
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import our time series utilities
from vedic_astrology_core.time_series import (
    compute_combined_series,
    compute_numerology_series,
    compute_planet_strength_series,
)

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    """Serve the main interactive page."""
    return render_template("timeline.html")


@app.route("/timeline")
def timeline():
    """Serve the timeline visualization page."""
    return render_template("timeline.html")


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
        }
    )


@app.route("/api/timeline-data")
def timeline_data():
    """Get timeline data for visualization."""
    try:
        # Get query parameters
        start_date = request.args.get(
            "start_date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        )
        end_date = request.args.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        step_days = int(request.args.get("step_days", 7))  # Default to weekly

        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Get data using our time series utilities
        planet_data = compute_planet_strength_series(start, end, step_days)
        numerology_data = compute_numerology_series(start, end, step_days)
        combined_data = compute_combined_series(start, end, step_days)

        return jsonify(
            {
                "success": True,
                "data": {
                    "planetary": planet_data,
                    "numerology": numerology_data,
                    "combined": combined_data,
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
