from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logic  # Importing your brain script

# 1. Initialize the App
app = FastAPI(title="Urban Growth Monitor API")

# 2. Enable CORS (Crucial for Streamlit connection)
# This allows your Frontend (Port 8501) to talk to this Backend (Port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Startup Event
# When the server starts, we want to log in to Google Earth Engine once.
@app.on_event("startup")
def startup_event():
    print("🚀 Starting up... Connecting to GEE...")
    logic.initialize_gee()

# 4. API Endpoints

@app.get("/")
def home():
    """Health Check Endpoint"""
    return {"message": "Urban Growth Monitor API is Live! 🌍"}

@app.get("/get-data")
def get_city_data(city: str):
    """
    Example: /get-data?city=Pune
    Calls the logic.analyze_city function.
    """
    print(f"📥 Received request for: {city}")
    
    # Call the brain
    result = logic.analyze_city(city)
    
    # Check for errors from logic.py
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result

# 5. Run the Server (if executed directly)
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)