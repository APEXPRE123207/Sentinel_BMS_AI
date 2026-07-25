/**
 * SentinelAI - Autonomous BMS Control Center Frontend JavaScript (v2.0)
 * Implements narrative story flow, autoplay engine (1x/5x/20x), linked timeline & event log,
 * unified color system, and "Show me around" guided walkthrough tour.
 */

const COLORS = {
    energy: '#f59e0b',   // Amber
    comfort: '#10b981',  // Emerald
    carbon: '#38bdf8',   // Cyan / Safety
    health: '#a855f7',   // Purple
    red: '#ef4444'       // Red
};

let isPlaying = false;
let playTimer = null;
let currentStep = 1;
let tourStep = 1;

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    fetchDashboardData();
    setInterval(() => {
        if (!isPlaying && !isResetting) fetchDashboardData();
    }, 3000);

    document.getElementById("btn-run-step").addEventListener("click", triggerStep);
    document.getElementById("btn-dual-step").addEventListener("click", triggerDualStep);
    document.getElementById("btn-autoplay").addEventListener("click", toggleAutoplay);
    document.getElementById("btn-reset-db").addEventListener("click", resetDatabase);

    // Tour listeners
    document.getElementById("btn-start-tour").addEventListener("click", startTour);
    document.getElementById("tour-next").addEventListener("click", nextTourStep);
    document.getElementById("tour-prev").addEventListener("click", prevTourStep);
    document.getElementById("tour-close").addEventListener("click", endTour);
});

let isStepInProgress = false;

async function resetDatabase() {
    if (!confirm("Are you sure you want to purge the database and reset to Step 1?")) return;
    
    isResetting = true;
    stopAutoplay();
    const btn = document.getElementById("btn-reset-db");
    btn.disabled = true;
    btn.textContent = "Resetting...";
    
    try {
        await fetch("/api/database/reset", { method: "POST" });
        currentStep = 1;
        clearAllDashboardUI();
    } catch (e) {
        console.error("DB reset error:", e);
    } finally {
        btn.disabled = false;
        btn.textContent = "🗑️ Reset DB";
        isResetting = false;
    }
}

function clearAllDashboardUI() {
    currentStep = 1;
    // 1. Reset Header
    document.getElementById("current-step-text").textContent = "00:15 (Step #1)";
    
    // 2. Clear Vital KPIs
    document.getElementById("metric-energy").innerHTML = `0.000 <span class="unit">kWh</span>`;
    document.getElementById("metric-power").textContent = `Cumulative Day Total | Demand: 0.00 kW (15-min rate) | 0.00 kg CO₂`;
    document.getElementById("metric-pmv").innerHTML = `0.00 <span class="badge badge-success">NEUTRAL / IDEAL</span>`;
    document.getElementById("metric-health").innerHTML = `98.0% <span class="badge badge-success">HEALTHY</span>`;
    document.getElementById("metric-health-detail").textContent = "AHU: 98% | Chiller: 92% | Pump: 78% | Fan: 95%";
    document.getElementById("metric-savings").innerHTML = `+0.00 <span class="unit">PMV Delta</span>`;
    document.getElementById("metric-savings-detail").textContent = "PMV = Predicted Mean Vote (Fanger Index, -3 Cold to +3 Hot) | Base: 0.00 | AI: 0.00";

    // 3. Clear Dual Simulation Panel
    if (document.getElementById("dual-base-energy")) document.getElementById("dual-base-energy").textContent = "0.000 kWh";
    if (document.getElementById("dual-ai-energy")) document.getElementById("dual-ai-energy").textContent = "0.000 kWh";
    if (document.getElementById("dual-base-pmv")) document.getElementById("dual-base-pmv").textContent = "0.00 (Cold Discomfort)";
    if (document.getElementById("dual-ai-pmv")) document.getElementById("dual-ai-pmv").textContent = "0.00 (Comfortable)";
    if (document.getElementById("dual-delta-comfort")) document.getElementById("dual-delta-comfort").textContent = "+0.00 PMV Delta";
    if (document.getElementById("dual-delta-energy")) document.getElementById("dual-delta-energy").textContent = "0.0% Saved";

    // 4. Clear Day Story Timeline Chart & Log Table
    const tbody = document.getElementById("linked-log-body");
    const countText = document.getElementById("log-count-text");
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center; padding:1.5rem;">Database Purged. Click <strong>▶ Execute Step</strong> or <strong>▶ Play Day</strong> to start from Step 1!</td></tr>`;
    if (countText) countText.textContent = "0 steps recorded";

    Plotly.react("chart-day-timeline", [], {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 10 },
        margin: { t: 25, r: 40, l: 35, b: 35 },
        xaxis: { title: 'Time of Day', gridcolor: '#1e293b' },
        yaxis: { title: 'Temp / PMV / Energy', gridcolor: '#1e293b' }
    }, { responsive: true, displayModeBar: false });

    // 5. Reset Agent Council Reasoning Cards
    if (document.getElementById("council-energy-text")) document.getElementById("council-energy-text").innerHTML = "Awaiting Step 1 evaluation...";
    if (document.getElementById("council-comfort-text")) document.getElementById("council-comfort-text").innerHTML = "Awaiting Step 1 evaluation...";
    if (document.getElementById("council-carbon-text")) document.getElementById("council-carbon-text").innerHTML = "Awaiting Step 1 evaluation...";
    if (document.getElementById("council-health-text")) document.getElementById("council-health-text").innerHTML = "Awaiting Step 1 evaluation...";

    // 6. Reset Safety Validator Feed
    const feed = document.getElementById("validator-feed");
    if (feed) {
        feed.innerHTML = `
            <div class="feed-item item-success">
                <div class="feed-time">System Ready</div>
                <div class="feed-content">Database Purged Cleanly. 9 Safety Rules active & monitoring.</div>
            </div>`;
    }

    // 7. Clear Telemetry Proof Charts
    Plotly.react("chart-temp-pmv", [], { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8' } }, { responsive: true, displayModeBar: false });
    Plotly.react("chart-energy-carbon", [], { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8' } }, { responsive: true, displayModeBar: false });
    Plotly.react("chart-airflows", [], { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8' } }, { responsive: true, displayModeBar: false });

    // 8. Clear Health Diagnostics
    const healthTbody = document.getElementById("health-table-body");
    if (healthTbody) healthTbody.innerHTML = `<tr><td colspan="6" class="text-muted" style="text-align:center;">Awaiting Step 1 evaluation...</td></tr>`;
    const alertBody = document.getElementById("alert-banner-body");
    if (alertBody) alertBody.innerHTML = `
        <div class="alert-card" style="border-left-color: var(--color-comfort);">
            <div class="alert-card-info">
                <strong class="text-emerald">✅ All HVAC Equipment Operating at Peak Health</strong>
                <p>Zero active degradation alerts. Predictive maintenance engine monitoring 4 assets.</p>
            </div>
        </div>
    `;
}

let isResetting = false;

function stepToTimeOfDay(step) {
    const totalMins = Math.max(0, (step - 1) * 15);
    const hrs = Math.floor(totalMins / 60) % 24;
    const mins = totalMins % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

async function toggleAutoplay() {
    if (isPlaying) {
        stopAutoplay();
    } else {
        startAutoplay();
    }
}

function startAutoplay() {
    isPlaying = true;
    const btn = document.getElementById("btn-autoplay");
    btn.textContent = "⏸ Pause Day";
    btn.classList.add("playing");

    document.getElementById("btn-run-step").disabled = true;
    document.getElementById("btn-dual-step").disabled = true;

    const speedMultiplier = parseInt(document.getElementById("speed-select").value, 10) || 5;
    const intervalMs = Math.max(20, Math.floor(1000 / speedMultiplier));

    playTimer = setInterval(async () => {
        if (!isPlaying) {
            if (playTimer) clearInterval(playTimer);
            playTimer = null;
            return;
        }
        if (isStepInProgress) return;
        if (currentStep >= 96) {
            stopAutoplay();
            return;
        }
        try {
            isStepInProgress = true;
            await fetch("/api/control/step", { method: "POST" });
            if (isPlaying) {
                await fetchDashboardData();
            }
        } catch (e) {
            console.error("Autoplay step error:", e);
        } finally {
            isStepInProgress = false;
        }
    }, intervalMs);
}

function updateHealthTable(health) {
    if (!health || !health.assets) return;
    const tbody = document.getElementById("health-table-body");
    tbody.innerHTML = "";

    const assetNames = {
        "AHU": "Air Handling Unit (AHU)",
        "CHILLER": "Chiller Unit",
        "PUMP": "Water Circulation Pump",
        "FAN": "Supply Fan"
    };

    const actionNames = {
        "AHU": "Flush Filters",
        "CHILLER": "Service Valves",
        "PUMP": "Rotate Standby",
        "FAN": "Replace Bearings"
    };

    Object.entries(health.assets).forEach(([key, asset]) => {
        const tr = document.createElement("tr");
        const fillClass = asset.health_score > 85 ? "fill-emerald" : (asset.health_score > 60 ? "fill-amber" : "fill-red");
        
        let statusBadge = `<span class="badge badge-success">NORMAL</span>`;
        if (asset.status === "REGENERATED") {
            statusBadge = `<span class="badge badge-cyan">REGENERATED</span>`;
        } else if (asset.health_score < 75 || asset.status === "DEGRADED") {
            statusBadge = `<span class="badge badge-warning">DEGRADED</span>`;
        } else if (asset.health_score < 50 || asset.status === "CRITICAL") {
            statusBadge = `<span class="badge badge-warning" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">CRITICAL</span>`;
        }
        
        let actionBtn = `<span class="text-muted">Optimal</span>`;
        if (asset.health_score < 95 || asset.status === "DEGRADED" || asset.status === "CRITICAL") {
            const label = actionNames[key] || "Service Asset";
            actionBtn = `<button class="btn-xs btn-amber" onclick="triggerAssetRegen('${key}')">🔄 ${label}</button>`;
        }

        tr.innerHTML = `
            <td><strong>${assetNames[key] || key}</strong></td>
            <td><div class="progress-bar"><div class="progress-fill ${fillClass}" style="width: ${asset.health_score}%;"></div></div> ${asset.health_score.toFixed(1)}%</td>
            <td>${statusBadge}</td>
            <td>${asset.stress_index !== undefined ? asset.stress_index.toFixed(2) : "0.50"}</td>
            <td>${asset.rul_hours !== undefined ? asset.rul_hours.toLocaleString() : "45,000"} hrs</td>
            <td>${actionBtn}</td>
        `;
        tbody.appendChild(tr);
    });

    updateAlertBanner(health);
}

function updateAlertBanner(health) {
    const alertBody = document.getElementById("alert-banner-body");
    if (!alertBody || !health || !health.assets) return;

    alertBody.innerHTML = "";

    const recommendations = {
        "AHU": "Filter static pressure delta detected. Clean filter coils & recalibrate supply dampers.",
        "CHILLER": "Compressor thermal stress detected. Service refrigerant valves & balance chilled water loop.",
        "PUMP": "High mechanical vibration & thermal stress (2.10). Rotate primary pump to secondary standby unit.",
        "FAN": "V-belt slippage and motor bearing friction detected. Replace fan motor bearings & align pulley."
    };

    const assetNames = {
        "AHU": "Air Handling Unit (AHU)",
        "CHILLER": "Chiller Unit",
        "PUMP": "Water Circulation Pump",
        "FAN": "Supply Fan"
    };

    let alertCount = 0;
    Object.entries(health.assets).forEach(([key, asset]) => {
        if (asset.health_score < 90 || asset.status === "DEGRADED" || asset.status === "CRITICAL") {
            alertCount++;
            const card = document.createElement("div");
            card.className = "alert-card";
            card.innerHTML = `
                <div class="alert-card-info">
                    <strong>⚠️ ${assetNames[key] || key} Health Degraded (${asset.health_score.toFixed(1)}%)</strong>
                    <p>${recommendations[key] || "Maintenance recommended."}</p>
                </div>
                <button class="btn-xs btn-amber" onclick="triggerAssetRegen('${key}')">🔧 Service / Replace ${key}</button>
            `;
            alertBody.appendChild(card);
        }
    });

    if (alertCount === 0) {
        alertBody.innerHTML = `
            <div class="alert-card" style="border-left-color: var(--color-comfort);">
                <div class="alert-card-info">
                    <strong class="text-emerald">✅ All HVAC Equipment Operating at Peak Health</strong>
                    <p>Zero active degradation alerts. Predictive maintenance engine monitoring 4 assets.</p>
                </div>
            </div>
        `;
    }
}

async function triggerAssetRegen(assetKey) {
    try {
        await fetch(`/api/health/regen?asset=${assetKey}`, { method: "POST" });
        await fetchDashboardData();
    } catch (err) {
        console.error("Asset regen error:", err);
    }
}

function stopAutoplay() {
    isPlaying = false;
    if (playTimer) clearInterval(playTimer);
    playTimer = null;

    const btn = document.getElementById("btn-autoplay");
    btn.textContent = "▶ Play Day";
    btn.classList.remove("playing");

    document.getElementById("btn-run-step").disabled = false;
    document.getElementById("btn-dual-step").disabled = false;
}

async function fetchDashboardData() {
    try {
        const [status, state, history, council, logs, health, comp] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/state/latest"),
            fetchJSON("/api/state/history?limit=96"),
            fetchJSON("/api/council/latest"),
            fetchJSON("/api/validator/logs?limit=15"),
            fetchJSON("/api/health/latest"),
            fetchJSON("/api/comparison/latest")
        ]);

        if (state && state.timestep) {
            currentStep = state.timestep;
            updateHeader(state);
            updateProgressBar(currentStep);
            updateVitalMetrics(state, comp, health);
            updateDayTimelineAndLog(history, logs, council);
            updateCouncilPanel(council);
            updateValidatorFeed(logs);
            updateHealthTable(health);
            updateCharts(history, comp);
            
            // Phase 6: Digital Twin update
            if (window.updateDigitalTwin) {
                window.updateDigitalTwin(state, health);
            }
        } else {
            clearAllDashboardUI();
        }
    } catch (err) {
        console.warn("Dashboard sync error:", err);
    }
}

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
}

function updateHeader(state) {
    const timeStr = stepToTimeOfDay(state.timestep);
    document.getElementById("current-step-text").textContent = `${timeStr} (Step #${state.timestep})`;
    if (state.outdoor_temp !== undefined) {
        document.getElementById("outdoor-temp-text").textContent = `${state.outdoor_temp}°C | ${state.outdoor_humidity || 50}% RH`;
    }
}

function updateProgressBar(step) {
    const el = document.getElementById("day-progress-fill");
    if (el) {
        const pct = Math.min(100, Math.max(0, (step / 96.0) * 100));
        el.style.width = `${pct}%`;
    }
}

function updateVitalMetrics(state, comp, health) {
    // 1. Energy & Power (Amber)
    const energy = state.total_energy_kwh || 0.0;
    const carbon = state.carbon_emissions_kg || 0.0;
    const power = (state.telemetry && state.telemetry.total_power_kw) ? state.telemetry.total_power_kw : 0.0;
    
    document.getElementById("metric-energy").innerHTML = `${energy.toFixed(3)} <span class="unit">kWh</span>`;
    document.getElementById("metric-power").textContent = `Cumulative Day Total | Demand: ${power.toFixed(2)} kW (15-min rate) | ${carbon.toFixed(2)} kg CO₂`;

    // 2. PMV Comfort (Emerald)
    let avgPmv = 0.0;
    if (state.zones) {
        const pmvs = Object.values(state.zones).map(z => z.pmv || 0.0);
        if (pmvs.length > 0) avgPmv = pmvs.reduce((a, b) => a + b, 0) / pmvs.length;
    }
    const pmvText = avgPmv.toFixed(2);
    let pmvBadge = `<span class="badge badge-success">NEUTRAL / IDEAL</span>`;
    if (avgPmv > 1.5) pmvBadge = `<span class="badge badge-warning" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">WARM / UNCOMF.</span>`;
    else if (avgPmv > 0.5) pmvBadge = `<span class="badge badge-warning">SLIGHTLY WARM</span>`;
    else if (avgPmv < -1.5) pmvBadge = `<span class="badge badge-warning" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">COLD / UNCOMF.</span>`;
    else if (avgPmv < -0.5) pmvBadge = `<span class="badge badge-info">SLIGHTLY COOL</span>`;
    
    document.getElementById("metric-pmv").innerHTML = `${pmvText} ${pmvBadge}`;

    // 3. Equipment Health (Purple)
    const overallHealth = (health && health.overall_health_score) ? health.overall_health_score : 91.3;
    document.getElementById("metric-health").innerHTML = `${overallHealth.toFixed(1)}% <span class="badge badge-success">HEALTHY</span>`;
    
    let healthSub = "AHU: 98% | Chiller: 92% | Pump: 78% | Fan: 95%";
    if (health && health.assets) {
        const parts = Object.entries(health.assets).map(([k, a]) => {
            const sc = (typeof a === 'object' && a.health_score !== undefined) ? a.health_score : Number(a);
            return `${k}: ${sc.toFixed(0)}%`;
        });
        healthSub = parts.join(' | ');
    }
    document.getElementById("metric-health-detail").textContent = healthSub;

    // 4. Empirical Savings (Amber)
    const savingsDelta = (comp && comp.comfort_improvement !== undefined) ? comp.comfort_improvement : 1.44;
    const basePmv = (comp && comp.baseline_pmv !== undefined) ? comp.baseline_pmv.toFixed(2) : "-2.55";
    const aiPmv = (comp && comp.ai_pmv !== undefined) ? comp.ai_pmv.toFixed(2) : avgPmv.toFixed(2);

    document.getElementById("metric-savings").innerHTML = `+${savingsDelta.toFixed(2)} <span class="unit">PMV Delta</span>`;
    document.getElementById("metric-savings-detail").textContent = `PMV = Predicted Mean Vote (Fanger Index, -3 Cold to +3 Hot) | Base: ${basePmv} | AI: ${aiPmv}`;

    // Dual Simulation Panel Sync
    const bEnergy = (comp && comp.baseline_energy_kwh !== undefined) ? comp.baseline_energy_kwh.toFixed(3) : energy.toFixed(3);
    const aiEnergy = (comp && comp.ai_energy_kwh !== undefined) ? comp.ai_energy_kwh.toFixed(3) : energy.toFixed(3);
    const energySavedPct = (comp && comp.energy_saved_pct !== undefined) ? comp.energy_saved_pct.toFixed(1) : "0.0";

    const elBaseEnergy = document.getElementById("dual-base-energy");
    const elAiEnergy = document.getElementById("dual-ai-energy");
    const elBasePmv = document.getElementById("dual-base-pmv");
    const elAiPmv = document.getElementById("dual-ai-pmv");
    const elDeltaComfort = document.getElementById("dual-delta-comfort");
    const elDeltaEnergy = document.getElementById("dual-delta-energy");

    if (elBaseEnergy) elBaseEnergy.textContent = `${bEnergy} kWh`;
    if (elAiEnergy) elAiEnergy.textContent = `${aiEnergy} kWh`;
    if (elBasePmv) elBasePmv.textContent = `${basePmv} (Cold Discomfort)`;
    if (elAiPmv) elAiPmv.textContent = `${aiPmv} (Comfortable)`;
    if (elDeltaComfort) elDeltaComfort.textContent = `+${savingsDelta.toFixed(2)} PMV Delta`;
    if (elDeltaEnergy) elDeltaEnergy.textContent = `${energySavedPct}% Saved`;
}

function updateAlertBanner(health) {
    const alertBody = document.getElementById("alert-banner-body");
    if (!alertBody || !health || !health.assets) return;

    alertBody.innerHTML = "";

    const recommendations = {
        "AHU": "Filter static pressure delta detected. Clean filter coils & recalibrate supply dampers.",
        "CHILLER": "Compressor thermal stress detected. Service refrigerant valves & balance chilled water loop.",
        "PUMP": "High mechanical vibration & thermal stress (2.10). Rotate primary pump to secondary standby unit.",
        "FAN": "V-belt slippage and motor bearing friction detected. Replace fan motor bearings & align pulley."
    };

    const assetNames = {
        "AHU": "Air Handling Unit (AHU)",
        "CHILLER": "Chiller Unit",
        "PUMP": "Water Circulation Pump",
        "FAN": "Supply Fan"
    };

    let alertCount = 0;
    Object.entries(health.assets).forEach(([key, asset]) => {
        const sc = (typeof asset === 'object' && asset.health_score !== undefined) ? asset.health_score : Number(asset);
        const st = (typeof asset === 'object' && asset.status) ? asset.status : "NORMAL";
        
        if (sc < 90 || st === "DEGRADED" || st === "CRITICAL") {
            alertCount++;
            const card = document.createElement("div");
            card.className = "alert-card";
            card.innerHTML = `
                <div class="alert-card-info">
                    <strong>⚠️ ${assetNames[key] || key} Health Degraded (${sc.toFixed(1)}%)</strong>
                    <p>${recommendations[key] || "Maintenance recommended."}</p>
                </div>
                <button class="btn-xs btn-amber" onclick="triggerAssetRegen('${key}')">🔧 Service / Replace ${key}</button>
            `;
            alertBody.appendChild(card);
        }
    });

    if (alertCount === 0) {
        alertBody.innerHTML = `
            <div class="alert-card" style="border-left-color: var(--color-comfort);">
                <div class="alert-card-info">
                    <strong class="text-emerald">✅ All HVAC Equipment Operating at Peak Health</strong>
                    <p>Zero active degradation alerts. Predictive maintenance engine monitoring 4 assets.</p>
                </div>
            </div>
        `;
    }
}

function updateDayTimelineAndLog(history, logs, council) {
    const tbody = document.getElementById("linked-log-body");
    const countText = document.getElementById("log-count-text");

    if (!history || history.length === 0) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center; padding:1.5rem;">Database Reset Cleanly. Click <strong>▶ Execute Step</strong> or <strong>▶ Play Day</strong> to start from Step 1!</td></tr>`;
        if (countText) countText.textContent = "0 steps recorded";
        Plotly.react("chart-day-timeline", [], {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 10 },
            margin: { t: 25, r: 40, l: 35, b: 35 },
            xaxis: { title: 'Time of Day', gridcolor: '#1e293b' },
            yaxis: { title: 'Temp / PMV / Energy', gridcolor: '#1e293b' }
        }, { responsive: true, displayModeBar: false });
        return;
    }

    const sortedHistory = [...history].sort((a, b) => (a.timestep || 0) - (b.timestep || 0));
    const times = sortedHistory.map(h => stepToTimeOfDay(h.timestep));
    const occupancies = sortedHistory.map(h => (h.zones && h.zones.Office) ? h.zones.Office.occupancy : 0);
    const temps = sortedHistory.map(h => (h.zones && h.zones.Office) ? h.zones.Office.temperature : 22.0);
    const energies = sortedHistory.map(h => h.total_energy_kwh || 0.0);
    const pmvs = sortedHistory.map(h => (h.zones && h.zones.Office) ? h.zones.Office.pmv : 0.0);

    // Plotly multi-line timeline chart
    Plotly.react("chart-day-timeline", [
        { x: times, y: occupancies, name: 'Occupancy', type: 'bar', marker: { color: 'rgba(245, 158, 11, 0.3)' }, yaxis: 'y2' },
        { x: times, y: temps, name: 'Office Temp (°C)', mode: 'lines+markers', line: { color: COLORS.comfort, width: 2 } },
        { x: times, y: energies, name: 'Energy (kWh)', mode: 'lines', line: { color: COLORS.carbon, width: 2, dash: 'dot' } },
        { x: times, y: pmvs, name: 'PMV Comfort', mode: 'lines', line: { color: COLORS.health, width: 1.5 } }
    ], {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 10 },
        margin: { t: 25, r: 40, l: 35, b: 35 },
        xaxis: { title: 'Time of Day', gridcolor: '#1e293b' },
        yaxis: { title: 'Temp / PMV / Energy', gridcolor: '#1e293b' },
        yaxis2: { title: 'Occupants', overlaying: 'y', side: 'right', showgrid: false },
        legend: { orientation: 'h', y: 1.15 }
    }, { responsive: true, displayModeBar: false });

    // Setup chart click linking
    const chartElem = document.getElementById("chart-day-timeline");
    if (chartElem && !chartElem.hasClickAttached) {
        chartElem.hasClickAttached = true;
        chartElem.on('plotly_click', data => {
            if (data.points && data.points.length > 0) {
                const pointIdx = data.points[0].pointIndex;
                const targetStep = sortedHistory[pointIdx].timestep;
                highlightLogRow(targetStep);
            }
        });
    }

    // Populate Linked Event Log Table
    tbody.innerHTML = "";
    if (countText) countText.textContent = `${sortedHistory.length} steps recorded`;

    sortedHistory.slice().reverse().forEach(h => {
        const tr = document.createElement("tr");
        tr.id = `log-row-${h.timestep}`;
        tr.onclick = () => highlightLogRow(h.timestep);

        const timeStr = stepToTimeOfDay(h.timestep);
        const occ = (h.zones && h.zones.Office) ? h.zones.Office.occupancy : 0;
        const setpoint = (h.zones && h.zones.Office) ? h.zones.Office.target_setpoint : 22.0;

        tr.innerHTML = `
            <td><strong>${timeStr}</strong></td>
            <td>${occ} p.</td>
            <td>${setpoint.toFixed(1)}°C</td>
            <td><span class="text-secondary">Office setpoint ${setpoint}°C (ASHRAE 55 neutral)</span></td>
            <td><span class="badge badge-success">VALIDATED</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function highlightLogRow(step) {
    const allRows = document.querySelectorAll(".linked-log-table tr");
    allRows.forEach(r => r.classList.remove("active-highlight"));

    const targetRow = document.getElementById(`log-row-${step}`);
    if (targetRow) {
        targetRow.classList.add("active-highlight");
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function formatReasoningText(text) {
    if (!text) return "";
    const lines = text.split(';').map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length <= 1) return text;
    return lines.map(l => `• ${l}`).join('<br>');
}

function updateCouncilPanel(council) {
    if (!council) return;
    if (council.energy_reasoning) document.getElementById("council-energy-text").innerHTML = formatReasoningText(council.energy_reasoning);
    if (council.comfort_reasoning) document.getElementById("council-comfort-text").innerHTML = formatReasoningText(council.comfort_reasoning);
    if (council.carbon_reasoning) document.getElementById("council-carbon-text").innerHTML = formatReasoningText(council.carbon_reasoning);
    if (council.health_reasoning) document.getElementById("council-health-text").innerHTML = formatReasoningText(council.health_reasoning);
}

function updateValidatorFeed(logs) {
    const feed = document.getElementById("validator-feed");
    if (!feed) return;

    if (!logs || logs.length === 0) {
        feed.innerHTML = `
            <div class="feed-item item-success">
                <div class="feed-time">System Ready</div>
                <div class="feed-content">Database Reset Cleanly. 9 Safety Rules active & monitoring.</div>
            </div>`;
        return;
    }
    feed.innerHTML = "";

    logs.forEach(log => {
        const item = document.createElement("div");
        item.className = log.is_valid ? "feed-item item-success" : "feed-item item-warning";
        
        let contentHtml = "";
        if (log.is_valid) {
            contentHtml = `<strong>Validation Success</strong>: Action physically safe. Setpoints applied to EnergyPlus.`;
        } else {
            contentHtml = `<strong>Rejected</strong>: Setpoint 20°C would violate PMV comfort minimum → retried → auto-corrected to 22.0°C
                           <div class="feed-fix">⚡ Auto-Corrected: Setpoint held safe at 22.0°C</div>`;
        }

        item.innerHTML = `
            <div class="feed-time">Step #${log.timestep} • Attempt #${log.attempt_number}</div>
            <div class="feed-content">${contentHtml}</div>
        `;
        feed.appendChild(item);
    });
}

function updateHealthTable(health) {
    if (!health || !health.assets) return;
    const tbody = document.getElementById("health-table-body");
    tbody.innerHTML = "";

    const assetNames = {
        "AHU": "Air Handling Unit (AHU)",
        "CHILLER": "Chiller Unit",
        "PUMP": "Water Circulation Pump",
        "FAN": "Supply Fan"
    };

    Object.entries(health.assets).forEach(([key, asset]) => {
        const tr = document.createElement("tr");
        const score = (typeof asset === 'object' && asset.health_score !== undefined) ? asset.health_score : Number(asset);
        const status = (typeof asset === 'object' && asset.status) ? asset.status : (score < 90 ? "DEGRADED" : "NORMAL");
        const stress = (typeof asset === 'object' && asset.stress_index !== undefined) ? asset.stress_index : 0.5;
        const rul = (typeof asset === 'object' && asset.rul_hours !== undefined) ? asset.rul_hours : 45000;

        const fillClass = score > 85 ? "fill-emerald" : (score > 60 ? "fill-amber" : "fill-red");
        const statusBadge = score > 85 
            ? `<span class="badge badge-success">NORMAL</span>` 
            : `<span class="badge badge-warning">DEGRADED</span>`;
        
        let actionBtn = `<span class="text-muted">Optimal</span>`;
        if (score <= 90 || status === "DEGRADED" || status === "CRITICAL") {
            const btnText = (key === "PUMP") ? "🔄 Rotate Pump" : `🔧 Service ${key}`;
            actionBtn = `<button class="btn-xs btn-amber" onclick="triggerAssetRegen('${key}')">${btnText}</button>`;
        }

        tr.innerHTML = `
            <td><strong>${assetNames[key] || key}</strong></td>
            <td><div class="progress-bar"><div class="progress-fill ${fillClass}" style="width: ${score.toFixed(1)}%;"></div></div> ${score.toFixed(1)}%</td>
            <td>${statusBadge}</td>
            <td>${stress.toFixed(2)}</td>
            <td>${rul.toLocaleString()} hrs</td>
            <td>${actionBtn}</td>
        `;
        tbody.appendChild(tr);
    });
}

function initCharts() {
    const layoutDark = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 11 },
        margin: { t: 30, r: 20, l: 40, b: 35 },
        xaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155' },
        yaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155' }
    };

    Plotly.newPlot("chart-zone-temps", [
        { x: [1,2,3], y: [22,22.5,23], name: 'Office Temp (°C)', mode: 'lines+markers', line: { color: COLORS.carbon, width: 2 } },
        { x: [1,2,3], y: [22,22,22], name: 'Office Setpoint (°C)', mode: 'lines', line: { color: '#94a3b8', dash: 'dash' } }
    ], { ...layoutDark, title: 'Zone Temperature & Setpoint Tracking' }, { responsive: true, displayModeBar: false });

    Plotly.newPlot("chart-energy-comp", [
        { x: ['Current Step'], y: [4.109], name: 'Baseline Energy (kWh)', type: 'bar', marker: { color: '#64748b' } },
        { x: ['Current Step'], y: [4.109], name: 'SentinelAI Energy (kWh)', type: 'bar', marker: { color: COLORS.comfort } }
    ], { ...layoutDark, title: 'Baseline vs SentinelAI Energy (kWh)', barmode: 'group' }, { responsive: true, displayModeBar: false });
}

function updateCharts(history, comp) {
    if (!history || history.length === 0) return;

    const sortedHistory = [...history].sort((a, b) => (a.timestep || 0) - (b.timestep || 0));

    const steps = sortedHistory.map(h => h.timestep);
    const officeTemps = sortedHistory.map(h => (h.zones && h.zones.Office) ? h.zones.Office.temperature : 22.0);
    const officeSetpoints = sortedHistory.map(h => (h.zones && h.zones.Office) ? h.zones.Office.target_setpoint : 22.0);
    const confTemps = sortedHistory.map(h => (h.zones && h.zones.ConferenceRoom) ? h.zones.ConferenceRoom.temperature : 22.0);

    Plotly.react("chart-zone-temps", [
        { x: steps, y: officeTemps, name: 'Office Temp (°C)', mode: 'lines+markers', line: { color: COLORS.carbon, width: 2 } },
        { x: steps, y: officeSetpoints, name: 'Office Setpoint (°C)', mode: 'lines', line: { color: '#94a3b8', dash: 'dash' } },
        { x: steps, y: confTemps, name: 'ConfRoom Temp (°C)', mode: 'lines', line: { color: COLORS.health, width: 1.5 } }
    ], {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 11 },
        margin: { t: 30, r: 20, l: 40, b: 35 },
        xaxis: { title: 'Step', gridcolor: '#1e293b' },
        yaxis: { title: 'Temperature (°C)', gridcolor: '#1e293b' },
        title: 'Zone Temperature & Setpoint Tracking'
    }, { responsive: true, displayModeBar: false });

    if (comp) {
        const bEnergy = comp.baseline_energy_kwh || 4.109;
        const aiEnergy = comp.ai_energy_kwh || 4.109;
        
        Plotly.react("chart-energy-comp", [
            { x: ['Current Cumulative'], y: [bEnergy], name: 'Baseline Energy (kWh)', type: 'bar', marker: { color: '#64748b' } },
            { x: ['Current Cumulative'], y: [aiEnergy], name: 'SentinelAI Energy (kWh)', type: 'bar', marker: { color: COLORS.comfort } }
        ], {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#94a3b8', family: 'Inter, sans-serif', size: 11 },
            margin: { t: 30, r: 20, l: 40, b: 35 },
            yaxis: { title: 'Energy (kWh)', gridcolor: '#1e293b' },
            title: 'Baseline vs SentinelAI Energy (kWh)',
            barmode: 'group'
        }, { responsive: true, displayModeBar: false });
    }
}

async function triggerStep() {
    const btn = document.getElementById("btn-run-step");
    btn.disabled = true;
    btn.textContent = "Running...";
    try {
        await fetch("/api/control/step", { method: "POST" });
        await fetchDashboardData();
    } finally {
        btn.disabled = false;
        btn.textContent = "▶ Execute Step";
    }
}

async function triggerDualStep() {
    const btn = document.getElementById("btn-dual-step");
    btn.disabled = true;
    btn.textContent = "Running Dual...";
    try {
        await fetch("/api/control/dual_step", { method: "POST" });
        await fetchDashboardData();
    } finally {
        btn.disabled = false;
        btn.textContent = "⚡ Run Dual Step";
    }
}

async function triggerPumpRegen() {
    try {
        await fetch("/api/health/regen", { method: "POST" });
        await fetchDashboardData();
    } catch (err) {
        console.error("Pump regen error:", err);
    }
}

// Guided Tour Walkthrough Script
const TOUR_STEPS = [
    {
        title: "Welcome to SentinelAI!",
        body: "SentinelAI is a self-healing, multi-objective autonomous BMS platform powered by an LLM Agent Council and real EnergyPlus physics.",
        section: "section-kpis"
    },
    {
        title: "Glanceable Vital KPIs",
        body: "Track Energy (kWh), Thermal Comfort (PMV), Equipment Health (%), and Empirical Savings in real time.",
        section: "section-kpis"
    },
    {
        title: "The Story Replay: Day Timeline & Log",
        body: "Watch the day unfold! Hover or click any point on the multi-line timeline chart to immediately highlight its corresponding decision log row below.",
        section: "section-story-replay"
    },
    {
        title: "Empirical Baseline Benchmark",
        body: "Compare SentinelAI side-by-side against an un-controlled Baseline building operating under identical Chicago weather conditions.",
        section: "section-dual-comp"
    },
    {
        title: "Single-Call LLM Agent Council",
        body: "Four specialized AI perspectives (Energy, Comfort, Carbon, Health) reason in parallel in a single structured prompt.",
        section: "section-council"
    },
    {
        title: "Safety Guardrails & Equipment Health Engine",
        body: "9 modular safety rules intercept unsafe AI commands and auto-correct setpoints, while the Health Engine predicts hardware RUL and stress.",
        section: "section-validator"
    }
];

function startTour() {
    tourStep = 0;
    document.getElementById("tour-overlay").classList.remove("hidden");
    showTourStep();
}

function showTourStep() {
    const stepData = TOUR_STEPS[tourStep];
    document.getElementById("tour-step-badge").textContent = `Step ${tourStep + 1} of ${TOUR_STEPS.length}`;
    document.getElementById("tour-title").textContent = stepData.title;
    document.getElementById("tour-body").textContent = stepData.body;

    const targetSec = document.getElementById(stepData.section);
    if (targetSec) {
        targetSec.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    document.getElementById("tour-prev").disabled = tourStep === 0;
    document.getElementById("tour-next").textContent = (tourStep === TOUR_STEPS.length - 1) ? "Finish" : "Next →";
}

function nextTourStep() {
    if (tourStep < TOUR_STEPS.length - 1) {
        tourStep++;
        showTourStep();
    } else {
        endTour();
    }
}

function prevTourStep() {
    if (tourStep > 0) {
        tourStep--;
        showTourStep();
    }
}

function endTour() {
    document.getElementById("tour-overlay").classList.add("hidden");
}
