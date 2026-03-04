import ee
import joblib
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

DB_NAME = "urban_growth.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS city_stats 
                      (city TEXT PRIMARY KEY, avg_radiance REAL, growth_rate REAL, 
                       status TEXT, confidence TEXT, last_updated DATE)''')
    conn.commit()
    conn.close()

def get_cached_data(city):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM city_stats WHERE city=?", (city,))
    row = cursor.fetchone()
    conn.close()
    if row: return {"city": row[0], "avg_radiance": row[1], "growth_rate": row[2], "status": row[3], "confidence": row[4], "source": "Database"}
    return None

def save_to_db(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO city_stats 
                      (city, avg_radiance, growth_rate, status, confidence, last_updated)
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (data['city'], data['avg_radiance'], data['growth_rate'], data['status'], data['confidence'], datetime.now()))
    conn.commit()
    conn.close()

def initialize_gee():
    init_db()
    try:
        service_account = 'fyp-bot@project1-473514.iam.gserviceaccount.com' 
        credentials = ee.ServiceAccountCredentials(service_account, 'ee-key.json')
        ee.Initialize(credentials)
        print("✅ GEE Connected Successfully")
    except Exception as e: print(f"❌ GEE Connection Failed: {e}")

try:
    model = joblib.load('model_v3.pkl')
    scaler = joblib.load('scaler_v3.pkl')
    print("✅ V3 Model & Scaler Loaded")
except Exception as e:
    print(f"⚠️ Error loading files: {e}"); model = None; scaler = None

def analyze_city(city_name):
    city_name = city_name.strip().title()
    cached = get_cached_data(city_name)
    if cached and 'heatmap_url' in cached: return cached

    print(f"🌍 FETCHING V3 DATA: {city_name}...")
    locations = {
        "Pune": {'lat': 18.5204, 'lon': 73.8567}, "Mumbai": {'lat': 19.0760, 'lon': 72.8777},
        "Delhi": {'lat': 28.7041, 'lon': 77.1025}, "Bangalore": {'lat': 12.9716, 'lon': 77.5946},
        "Kolhapur": {'lat': 16.7050, 'lon': 74.2433}
    }
    if city_name not in locations: return {"error": f"City '{city_name}' not supported."}
    coords = locations[city_name]
    point = ee.Geometry.Point(coords['lon'], coords['lat'])
    
    outer_circle = point.buffer(15000)
    inner_circle = point.buffer(5000)
    donut_ring = outer_circle.difference(inner_circle)

    def mask_clouds(image): return image.updateMask(image.select('cf_cvg').gt(0))
    collection = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG").map(mask_clouds)
    img_old = collection.filterDate('2023-01-01', '2024-01-01').select('avg_rad').mean()
    img_new = collection.filterDate('2024-01-01', '2025-01-01').select('avg_rad').mean()

    try:
        combined_reducer = ee.Reducer.mean().combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True)
        old_stats = img_old.reduceRegion(combined_reducer, donut_ring, 500).getInfo()
        new_stats = img_new.reduceRegion(combined_reducer, donut_ring, 500).getInfo()
        
        prev_rad = old_stats.get('avg_rad_mean', 0) or 0
        curr_rad = new_stats.get('avg_rad_mean', 0) or 0
        patchiness = new_stats.get('avg_rad_stdDev', 0) or 0
    except Exception as e: return {"error": str(e)}

    radiance_growth = (curr_rad - prev_rad) / prev_rad if prev_rad > 0 else 0
    poi_density = {"Mumbai": 45.0, "Pune": 30.0}.get(city_name, 25.0)

    calibrated_momentum = radiance_growth
    infra_signal = (poi_density * curr_rad) / 100
    features = np.array([[curr_rad, poi_density, calibrated_momentum, infra_signal, patchiness]])
    
    scaled_features = scaler.transform(features) if scaler else features 
    if model:
        pred_class = model.predict(scaled_features)[0]
        status = "High Growth 🟢" if pred_class == 1 else "Stagnant 🔴"
        confidence = f"{round(np.max(model.predict_proba(scaled_features)) * 100, 1)}%"
    else: status = "Unknown"; confidence = "0%"

   # ==========================================
    # VISUAL FIX: The Authentic Pixelated Batrak Map
    # ==========================================
    # We keep the lower threshold (30) so it glows bright, but remove the smoothing!
    vis_params = {'min': 0.5, 'max': 30.0, 'palette': ['4B0082', '0000FF', '00FF00', 'FFFF00', 'FF0000']}
    
    # Update mask makes the empty areas transparent so streets show through
    masked_img = img_new.updateMask(img_new.gt(0.5)) 
    
    # Generate the raw, pixelated URL
    heatmap_url = masked_img.clip(outer_circle).getMapId(vis_params)['tile_fetcher'].url_format
    
    timeline_years = ['2021', '2022', '2023', '2024', '2025']
    timeline_radiance = []
    for y in timeline_years:
        try:
            h_img = collection.filterDate(f'{y}-01-01', f'{int(y)+1}-01-01').select('avg_rad').mean()
            h_rad = h_img.reduceRegion(ee.Reducer.mean(), donut_ring, 500).getInfo().get('avg_rad', 0)
            timeline_radiance.append(round(h_rad if h_rad else 0, 2))
        except: timeline_radiance.append(0)

    gdp_proxies = {"Pune": [7.1, 7.8, 8.2, 8.5, 9.1], "Mumbai": [6.0, 6.2, 6.5, 6.8, 7.1]}

    result = {
        "city": city_name, "avg_radiance": round(curr_rad, 2), "growth_rate": round(radiance_growth * 100, 2),
        "patchiness": round(patchiness, 2), "status": status, "confidence": confidence,
        "heatmap_url": heatmap_url, "timeline_years": timeline_years, 
        "timeline_radiance": timeline_radiance, "timeline_gdp": gdp_proxies.get(city_name, [5.0, 5.5, 6.0, 6.5, 7.0])
    }
    save_to_db(result)
    return result