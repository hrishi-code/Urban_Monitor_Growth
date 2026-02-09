import ee
import joblib
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

# ==========================================
# 1. DATABASE SETUP (The Memory)
# ==========================================
DB_NAME = "urban_growth.db"

def init_db():
    """Creates the table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS city_stats (
            city TEXT PRIMARY KEY,
            avg_radiance REAL,
            growth_rate REAL,
            status TEXT,
            confidence TEXT,
            last_updated DATE
        )
    ''')
    conn.commit()
    conn.close()

def get_cached_data(city):
    """Checks if we already have data for this city."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM city_stats WHERE city=?", (city,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"⚡ CACHE HIT: Found {city} in database!")
        return {
            "city": row[0],
            "avg_radiance": row[1],
            "growth_rate": row[2],
            "status": row[3],
            "confidence": row[4],
            "source": "Database (Instant)"
        }
    return None

def save_to_db(data):
    """Saves new data to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO city_stats 
        (city, avg_radiance, growth_rate, status, confidence, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['city'], data['avg_radiance'], data['growth_rate'], 
          data['status'], data['confidence'], datetime.now()))
    conn.commit()
    conn.close()
    print(f"💾 SAVED: {data['city']} saved to database.")

# ==========================================
# 2. SETUP & AUTH
# ==========================================
def initialize_gee():
    # Initialize DB first
    init_db()
    
    try:
        service_account = 'fyp-bot@project1-473514.iam.gserviceaccount.com' # <--- VERIFY THIS EMAIL
        credentials = ee.ServiceAccountCredentials(service_account, 'ee-key.json')
        ee.Initialize(credentials)
        print("✅ GEE Connected Successfully")
    except Exception as e:
        print(f"❌ GEE Connection Failed: {e}")

# ==========================================
# 3. LOAD BRAIN & SCALER
# ==========================================
try:
    model = joblib.load('model.pkl')
    scaler = joblib.load('scaler.pkl')
    print("✅ Model & Scaler Loaded")
except Exception as e:
    print(f"⚠️ Error loading files: {e}")
    model = None
    scaler = None

# ==========================================
# 4. CORE LOGIC (Now with Database Check)
# ==========================================
def analyze_city(city_name):
    # STEP A: Check Database First
    cached = get_cached_data(city_name)
    if cached:
        return cached

    # STEP B: If not in DB, fetch from Google
    print(f"🌍 FETCHING: Downloading data for {city_name} from Google Earth Engine...")
    
    locations = {
        "Pune": {'lat': 18.5204, 'lon': 73.8567},
        "Mumbai": {'lat': 19.0760, 'lon': 72.8777},
        "Delhi": {'lat': 28.7041, 'lon': 77.1025},
        "Bangalore": {'lat': 12.9716, 'lon': 77.5946}
    }
    
    if city_name not in locations:
        return {"error": "City not supported"}
        
    coords = locations[city_name]
    point = ee.Geometry.Point(coords['lon'], coords['lat'])
    
    # Get Data (Using known good range)
    dataset = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG") \
                .filterDate('2023-01-01', '2023-04-01') \
                .select('avg_rad')
    
    images = dataset.toList(2)
    if images.size().getInfo() < 2:
        return {"error": "Not enough satellite data found"}

    curr_rad = ee.Image(images.get(1)).reduceRegion(ee.Reducer.mean(), point.buffer(5000), 500).getInfo().get('avg_rad', 0)
    prev_rad = ee.Image(images.get(0)).reduceRegion(ee.Reducer.mean(), point.buffer(5000), 500).getInfo().get('avg_rad', 0)
    
    # Calculate Features
    avg_radiance = curr_rad
    radiance_growth = (curr_rad - prev_rad) / prev_rad if prev_rad > 0 else 0
    poi_density = {"Mumbai": 45.0, "Pune": 30.0}.get(city_name, 25.0)

    # Prepare for AI
    features = np.array([[avg_radiance, radiance_growth, poi_density]])
    if scaler:
        scaled_features = scaler.transform(features)
    else:
        scaled_features = features 

    # Predict
    if model:
        pred_class = model.predict(scaled_features)[0]
        status = "High Growth 🟢" if pred_class == 1 else "Stagnant 🔴"
        confidence = f"{round(np.max(model.predict_proba(scaled_features)) * 100, 1)}%"
    else:
        status = "Unknown"
        confidence = "0%"

    # Create Result
    result = {
        "city": city_name,
        "avg_radiance": round(avg_radiance, 2),
        "growth_rate": round(radiance_growth * 100, 2),
        "status": status,
        "confidence": confidence,
        "source": "Google Earth Engine (Live)"
    }
    
    # STEP C: Save to Database for next time
    save_to_db(result)
    
    return result

if __name__ == "__main__":
    initialize_gee()
    print(analyze_city("Pune"))