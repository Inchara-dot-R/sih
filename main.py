"""
Minimal FastAPI backend for the Dam Break Flood Platform prototype.

Run with:
    uvicorn main:app --reload --port 8000
(run this command from inside the backend/ folder)
"""

import json
import os
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dam Break Flood Platform - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts", "data")

DAM_SITE = {
    "name": "Bhakra Dam",
    "lat": 31.4166,
    "lon": 76.4291,
}


@app.get("/")
def root():
    return {"status": "ok", "message": "Dam Break Flood Platform backend is running"}


@app.get("/api/dam-site")
def get_dam_site():
    return DAM_SITE


@app.get("/api/layers/roads")
def get_roads():
    return load_geojson("roads.geojson")


@app.get("/api/layers/buildings")
def get_buildings():
    return load_geojson("buildings.geojson")


def load_geojson(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {"type": "FeatureCollection", "features": []}
    with open(path) as f:
        return json.load(f)


@app.get("/api/flood-summary")
def get_flood_summary():
    path = os.path.join(DATA_DIR, "flood_risk.npz")

    if not os.path.exists(path):
        return {"status": "error", "message": "Flood risk data not found"}

    data = np.load(path)

    depth = data["depth"]
    risk = data["risk"]

    return {
        "status": "ok",
        "maximum_depth_m": float(np.max(depth)),
        "safe_cells": int(np.sum(risk == 0)),
        "low_cells": int(np.sum(risk == 1)),
        "moderate_cells": int(np.sum(risk == 2)),
        "high_cells": int(np.sum(risk == 3)),
        "critical_cells": int(np.sum(risk == 4))
    }


@app.get("/api/flood-extent")
def get_flood_extent():
    """
    Returns flooded cells as GeoJSON points, using the coordinates that
    were saved directly alongside the flood risk data itself.
    Only returns cells with risk > 0 to keep the response a reasonable size.
    """
    risk_path = os.path.join(DATA_DIR, "flood_risk.npz")

    if not os.path.exists(risk_path):
        return {"type": "FeatureCollection", "features": []}

    risk_data = np.load(risk_path)

    x = risk_data["x"]
    y = risk_data["y"]
    depth = risk_data["depth"]
    risk = risk_data["risk"]

    if x.ndim == 1 and y.ndim == 1:
        X, Y = np.meshgrid(x, y)
    else:
        X, Y = x, y

    X_flat = X.flatten()
    Y_flat = Y.flatten()
    depth_flat = depth.flatten()
    risk_flat = risk.flatten()

    if not (len(X_flat) == len(Y_flat) == len(depth_flat) == len(risk_flat)):
        return {
            "status": "error",
            "message": (
                f"Shape mismatch after flattening -- X:{len(X_flat)} "
                f"Y:{len(Y_flat)} depth:{len(depth_flat)} risk:{len(risk_flat)}"
            ),
        }

    flooded_mask = risk_flat > 0

    features = []
    for fx, fy, fd, fr in zip(
        X_flat[flooded_mask], Y_flat[flooded_mask],
        depth_flat[flooded_mask], risk_flat[flooded_mask]
    ):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(fx), float(fy)]},
            "properties": {
                "depth_m": round(float(fd), 2),
                "risk": int(fr),
            },
        })

    return {"type": "FeatureCollection", "features": features}


@app.get("/api/evacuation-route")
def get_evacuation_route():
    path = os.path.join(DATA_DIR, "before_the_wave_route.json")

    if not os.path.exists(path):
        return {"status": "error", "message": "Evacuation route not found"}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/final-decision")
def get_final_decision():
    path = os.path.join(DATA_DIR, "before_the_wave_final_decision.json")

    if not os.path.exists(path):
        return {"status": "error", "message": "Final decision not found"}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)