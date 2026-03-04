from flask import Flask, render_template, request, jsonify
import logic  
import os

app = Flask(__name__)

print("🚀 Starting Server...")
logic.initialize_gee()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        # 1. Grab the input and clean it up instantly
        city_input = data.get('city', 'Pune')
        clean_city = city_input.strip().title() 
        
        print(f"📥 Analyzing: {clean_city}")
        
        # 2. Call the AI Brain with the clean name
        result = logic.analyze_city(clean_city)
        print("🚨 BACKEND RAW OUTPUT:", result)
        
        # 3. Add Kolhapur to the dictionary!
        coords_map = {
            "Pune": [18.5204, 73.8567],
            "Mumbai": [19.0760, 72.8777],
            "Delhi": [28.7041, 77.1025],
            "Bangalore": [12.9716, 77.5946],
            "Kolhapur": [16.7050, 74.2433]
        }
        
        # Use the clean_city to fetch the right coordinates
        result['coords'] = coords_map.get(clean_city, [20.5937, 78.9629])
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)