// 1. Initialize Map
var map = L.map('map').setView([20.5937, 78.9629], 5); // Center of India

// Add Dark Mode Map Tiles (CartoDB DarkMatter)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

// Marker Variable
var currentMarker = null;

async function runPrediction() {
    let city = document.getElementById("citySelect").value;
    let resultsPanel = document.getElementById("resultsPanel");
    let status = document.getElementById("aiStatus");
    
    // Show loading state
    status.innerText = "Scanning...";
    resultsPanel.classList.remove("d-none");

    try {
        // Call Flask API
        let response = await fetch('/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city: city })
        });
        
        let data = await response.json();

        if (data.error) {
            alert("Error: " + data.error);
            return;
        }

        // Update UI
        status.innerText = data.status;
        status.className = data.status.includes("High") ? "text-center text-success fw-bold" : "text-center text-danger fw-bold";
        
        document.getElementById("aiConf").innerText = "Confidence: " + data.confidence;
        document.getElementById("valRadiance").innerText = data.avg_radiance + " nW";
        document.getElementById("valGrowth").innerText = data.growth_rate + "%";

        // Update Map
        let lat = data.coords[0];
        let lng = data.coords[1];

        map.flyTo([lat, lng], 12); // Smooth zoom

        if (currentMarker) {
            map.removeLayer(currentMarker);
        }

        // Add Heatmap-style Circle
        currentMarker = L.circle([lat, lng], {
            color: data.status.includes("High") ? '#00d26a' : '#ff4b4b',
            fillColor: data.status.includes("High") ? '#00d26a' : '#ff4b4b',
            fillOpacity: 0.5,
            radius: 3000
        }).addTo(map);

        currentMarker.bindPopup(`<b>${city}</b><br>Status: ${data.status}<br>Light: ${data.avg_radiance} nW`).openPopup();

    } catch (error) {
        console.error("Error:", error);
        alert("Failed to connect to backend.");
    }
}