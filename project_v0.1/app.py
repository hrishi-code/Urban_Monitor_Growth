from flask import Flask, render_template, request, jsonify
import logic  # Your existing AI script
import os

app = Flask(__name__)

# Initialize GEE on startup
print("🚀 Starting Server...")
logic.initialize_gee()

@app.route('/')
def home():
    """Renders the main dashboard."""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """API Endpoint called by the Frontend JS."""
    try:
        data = request.json
        city = data.get('city', 'Pune')
        
        print(f"📥 Analyzing: {city}")
        
        # Call your existing AI Brain
        result = logic.analyze_city(city)
        
        # Add map coordinates for the frontend to center the map
        coords_map = {
            "Pune": [18.5204, 73.8567],
            "Mumbai": [19.0760, 72.8777],
            "Delhi": [28.7041, 77.1025],
            "Bangalore": [12.9716, 77.5946]
        }
        result['coords'] = coords_map.get(city, [20.5937, 78.9629])
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # AWS often needs host='0.0.0.0'
    app.run(debug=True, host='0.0.0.0', port=5000)