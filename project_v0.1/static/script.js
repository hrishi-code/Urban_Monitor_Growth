var map = L.map('map').setView([20.5937, 78.9629], 5);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);

var cityLayer = null, donutRing = null, heatmapLayer = null, growthChart = null; 
var poiLayerGroup = L.layerGroup().addTo(map);

async function runPrediction() {
    let city = document.getElementById("cityInput").value.trim();
    if (!city) return;

    let btn = document.getElementById("btnAnalyze");
    btn.innerHTML = 'Scanning...'; btn.disabled = true;

    try {
        let response = await fetch('/predict', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ city: city })
        });
        let data = await response.json();
        if (data.error) throw new Error(data.error);

        document.getElementById("cityNameDisplay").innerText = data.city;
        document.getElementById("valRadiance").innerText = data.avg_radiance;
        document.getElementById("valPatchiness").innerText = data.patchiness || '--'; 
        
        let gVal = document.getElementById("valGrowth");
        gVal.innerText = `${data.growth_rate > 0 ? '+' : ''}${data.growth_rate}%`;
        gVal.className = data.growth_rate > 0 ? "text-success mt-1" : "text-danger mt-1";

        let isGrowth = data.status.includes("High");
        let badge = document.getElementById("aiStatusBadge");
        badge.innerText = `${data.status} (${data.confidence})`;
        badge.style.backgroundColor = isGrowth ? "rgba(0, 255, 0, 0.1)" : "rgba(255, 0, 0, 0.1)";
        badge.style.color = isGrowth ? "#00ff00" : "#ff4444";
        badge.style.border = `1px solid ${isGrowth ? "#00ff00" : "#ff4444"}`;

        let lat = data.coords ? data.coords[0] : 18.5204;
        let lng = data.coords ? data.coords[1] : 73.8567;
        
        // ==========================================
        // UI FIX: Wait 400ms to eliminate the grey map bug!
        // ==========================================
        setTimeout(() => {
            map.invalidateSize(); 
            map.flyTo([lat, lng], 11);
        }, 400);

        if (cityLayer) map.removeLayer(cityLayer);
        if (donutRing) map.removeLayer(donutRing);
        if (heatmapLayer) map.removeLayer(heatmapLayer);
        poiLayerGroup.clearLayers();

        cityLayer = L.circle([lat, lng], { color: '#ff0000', fillColor: '#ff0000', fillOpacity: 0.3, radius: 5000 }).bindPopup("Ignored Saturated Core").addTo(map);
        donutRing = L.circle([lat, lng], { color: '#00ffff', fillOpacity: 0.0, weight: 2, dashArray: '5, 5', radius: 15000 }).addTo(map);
        
        if (data.heatmap_url) heatmapLayer = L.tileLayer(data.heatmap_url, { opacity: 0.75 }).addTo(map);

        fetchAndPlotPOIs(lat, lng);
        updateChart(data.timeline_years, data.timeline_radiance, data.timeline_gdp);

    } catch (e) { alert("Error: " + e.message); } 
    finally { btn.innerHTML = 'Run Scan'; btn.disabled = false; }
}

async function fetchAndPlotPOIs(lat, lng) {
    let query = `[out:json][timeout:15];(node["amenity"~"pub|bar|nightclub"](around:15000,${lat},${lng});node["shop"~"mall|supermarket"](around:15000,${lat},${lng}););out body limit 300;`;
    let url = "https://overpass-api.de/api/interpreter?data=" + encodeURIComponent(query);
    try {
        let res = await fetch(url); let data = await res.json();
        data.elements.forEach(poi => {
            let isNightlife = poi.tags.amenity !== undefined;
            let dotColor = isNightlife ? '#ff00ff' : '#00ffff'; 
            L.circleMarker([poi.lat, poi.lon], {radius: 4, fillColor: dotColor, color: '#ffffff', weight: 1, opacity: 1, fillOpacity: 0.9}).addTo(poiLayerGroup);
        });
    } catch(e) {}
}

function updateChart(years, radianceData, gdpData) {
    let ctx = document.getElementById('growthChart').getContext('2d');
    if (growthChart) growthChart.destroy();
    growthChart = new Chart(ctx, {
        type: 'line',
        data: { labels: years, datasets: [
            { label: 'Avg Radiance', data: radianceData, borderColor: '#00ffff', backgroundColor: 'rgba(0, 255, 255, 0.1)', borderWidth: 3, tension: 0.4, yAxisID: 'y' },
            { label: 'GDP Proxy (%)', data: gdpData, borderColor: '#ff00ff', borderDash: [5, 5], borderWidth: 2, tension: 0.4, yAxisID: 'y1' }
        ]},
        options: { responsive: true, scales: { x: { ticks: { color: '#aaa' } }, y: { ticks: { color: '#00ffff' } }, y1: { position: 'right', ticks: { color: '#ff00ff' }, grid: { drawOnChartArea: false } } }, plugins: { legend: { labels: { color: '#fff' } } } }
    });
}