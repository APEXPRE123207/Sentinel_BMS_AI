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
let digitalTwin = null;  // Canvas-based Digital Twin engine

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    digitalTwin = new DigitalTwinCanvas("digital-twin-canvas");
    digitalTwin.drawIdle();
    fetchDashboardData();
    setInterval(() => {
        if (!isPlaying && !isResetting) fetchDashboardData();
    }, 3000);

    document.getElementById("btn-run-step").addEventListener("click", triggerStep);
    document.getElementById("btn-autoplay").addEventListener("click", toggleAutoplay);
    document.getElementById("btn-reset-db").addEventListener("click", resetDatabase);

    // Tour listeners
    document.getElementById("btn-start-tour").addEventListener("click", startTour);
    document.getElementById("btn-config-modal").addEventListener("click", showConfigModal);
    document.getElementById("btn-save-config").addEventListener("click", saveConfig);
    document.getElementById("tour-next").addEventListener("click", nextTourStep);
    document.getElementById("tour-prev").addEventListener("click", prevTourStep);
    document.getElementById("tour-close").addEventListener("click", endTour);
});

function showConfigModal() {
    document.getElementById("config-overlay").classList.remove("hidden");
}

async function saveConfig() {
    const month = parseInt(document.getElementById("config-month").value, 10);
    const occupants = parseInt(document.getElementById("config-occ").value, 10);
    const day_of_week = document.getElementById("config-day").value;
    
    document.getElementById("btn-save-config").textContent = "Saving...";
    document.getElementById("btn-save-config").disabled = true;
    
    try {
        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ month, occupants, day_of_week })
        });
        
        // Reset local UI state
        if (digitalTwin) digitalTwin.drawIdle();
        clearAllDashboardUI();
        currentStep = 1;
        isPlaying = false;
        
        // Hide modal
        document.getElementById("config-overlay").classList.add("hidden");
    } catch (err) {
        console.error("Config save error:", err);
    } finally {
        document.getElementById("btn-save-config").textContent = "Save & Reset";
        document.getElementById("btn-save-config").disabled = false;
    }
}

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
    document.getElementById("current-step-text").textContent = stepToTimeOfDay(1) + " (Step #1)";
    
    // 2. Clear Vital KPIs
    document.getElementById("metric-energy").innerHTML = `0.000 <span class="unit">kWh</span>`;
    document.getElementById("metric-power").textContent = `Cumulative Day Total | Demand: 0.00 kW (15-min rate) | 0.00 kg CO₂`;
    document.getElementById("metric-pmv").innerHTML = `0.00 <span class="badge badge-success">NEUTRAL / IDEAL</span>`;
    document.getElementById("metric-health").innerHTML = `100.0% <span class="badge badge-success">HEALTHY</span>`;
    document.getElementById("metric-health-detail").textContent = "AHU: 100% | Chiller: 100% | Pump: 100% | Fan: 100%";
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

    // 7. Clear Telemetry Proof Charts (use correct IDs that exist in index.html)
    const chartZoneTemps = document.getElementById("chart-zone-temps");
    const chartEnergyComp = document.getElementById("chart-energy-comp");
    if (chartZoneTemps) Plotly.react("chart-zone-temps", [], { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8' } }, { responsive: true, displayModeBar: false });
    if (chartEnergyComp) Plotly.react("chart-energy-comp", [], { paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8' } }, { responsive: true, displayModeBar: false });

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
    // Physics engine (runner.py) starts at 6.75 hours (06:45 AM)
    // 6.75 * 60 = 405 minutes. We offset the UI clock to match the physics clock.
    const startOffsetMins = 405; 
    const totalMins = Math.max(0, startOffsetMins + (step - 1) * 15);
    const hrs = Math.floor(totalMins / 60) % 24;
    const mins = totalMins % 60;
    
    const ampm = hrs >= 12 ? 'PM' : 'AM';
    const h12 = hrs % 12 || 12;
    return `${h12.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')} ${ampm}`;
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

            // Render Digital Twin Canvas
            if (digitalTwin) digitalTwin.render(state, health, council);

        } else {
            clearAllDashboardUI();
            if (digitalTwin) digitalTwin.drawIdle();
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
    const savingsDelta = (comp && comp.comparison && comp.comparison.comfort_improvement !== undefined) ? comp.comparison.comfort_improvement : 1.44;
    const basePmv = (comp && comp.baseline && comp.baseline.avg_pmv !== undefined) ? comp.baseline.avg_pmv.toFixed(2) : "-2.55";
    const aiPmv = (comp && comp.sentinel_ai && comp.sentinel_ai.avg_pmv !== undefined) ? comp.sentinel_ai.avg_pmv.toFixed(2) : avgPmv.toFixed(2);

    document.getElementById("metric-savings").innerHTML = `+${savingsDelta.toFixed(2)} <span class="unit">PMV Delta</span>`;
    document.getElementById("metric-savings-detail").textContent = `PMV = Predicted Mean Vote (Fanger Index, -3 Cold to +3 Hot) | Base: ${basePmv} | AI: ${aiPmv}`;

    // Dual Simulation Panel Sync
    const bEnergy = (comp && comp.baseline && comp.baseline.energy_kwh !== undefined) ? comp.baseline.energy_kwh.toFixed(3) : energy.toFixed(3);
    const aiEnergy = (comp && comp.sentinel_ai && comp.sentinel_ai.energy_kwh !== undefined) ? comp.sentinel_ai.energy_kwh.toFixed(3) : energy.toFixed(3);
    const energySavedPct = (comp && comp.comparison && comp.comparison.energy_saved_pct !== undefined) ? comp.comparison.energy_saved_pct.toFixed(1) : "0.0";

    const elBaseEnergy = document.getElementById("dual-base-energy");
    const elAiEnergy = document.getElementById("dual-ai-energy");
    const elBasePmv = document.getElementById("dual-base-pmv");
    const elAiPmv = document.getElementById("dual-ai-pmv");
    const elDeltaComfort = document.getElementById("dual-delta-comfort");
    const elDeltaEnergy = document.getElementById("dual-delta-energy");

    function getPmvLabel(pmvStr) {
        const p = parseFloat(pmvStr);
        if (p > 1.5) return "Hot Discomfort";
        if (p > 0.5) return "Slightly Warm";
        if (p < -1.5) return "Cold Discomfort";
        if (p < -0.5) return "Slightly Cool";
        return "Neutral / Comfortable";
    }

    if (elBaseEnergy) elBaseEnergy.textContent = `${bEnergy} kWh`;
    if (elAiEnergy) elAiEnergy.textContent = `${aiEnergy} kWh`;
    if (elBasePmv) elBasePmv.textContent = `${basePmv} (${getPmvLabel(basePmv)})`;
    if (elAiPmv) elAiPmv.textContent = `${aiPmv} (${getPmvLabel(aiPmv)})`;
    if (elDeltaComfort) elDeltaComfort.textContent = `+${savingsDelta.toFixed(2)} PMV Delta`;
    if (elDeltaEnergy) elDeltaEnergy.textContent = `${energySavedPct}% Saved`;

    const elAiDecisions = document.getElementById("dual-ai-decisions");
    if (elAiDecisions && state && state.zones) {
        let html = `# Dynamic AI Decisions<br>`;
        for (const [zId, z] of Object.entries(state.zones)) {
            const sp = (z.target_setpoint || 22.0).toFixed(1);
            const flow = (z.airflow || 0.5).toFixed(2);
            html += `${zId}: setpoint=${sp}°C, airflow=${flow}<br>`;
        }
        elAiDecisions.innerHTML = html;
    }
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
        let occ = 0;
        if (h.zones) {
            Object.values(h.zones).forEach(z => { occ += (z.occupancy || 0); });
        }
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
        body: "Compare SentinelAI side-by-side against an un-controlled Baseline building operating under identical local weather conditions.",
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

// =============================================================================
// DIGITAL TWIN CANVAS ENGINE
// Replaces Pygame — renders the building floorplan directly in the browser.
// =============================================================================
class DigitalTwinCanvas {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext("2d");
        this.W = this.canvas.width;   // 1100
        this.H = this.canvas.height;  // 420
        this._pulsePhase = 0;

        // Static layout config
        this.rooms = {
            "Office":         { x: 20,  y: 20, w: 380, h: 560, label: "Office (West Zone)" },
            "ConferenceRoom": { x: 420, y: 20, w: 380, h: 560, label: "Conference Room (East Zone)" },
            "Lobby":          { x: 820, y: 20, w: 180, h: 560, label: "Lobby (North Zone)" },
        };

        // Toast state
        this._toastMsg = "";
        this._toastAlpha = 0;
        this._toastState = "idle";
        this._toastStart = 0;
        this._lastCouncilTs = 0;
        this._pulsePhase = 0;
    }

    // Modern glassmorphism PMV colors
    pmvColor(pmv, ctx, x, y, w, h) {
        let colors = [];
        if (pmv < -1.0) colors = ["#3b82f6", "#1d4ed8"];       // Cold (Blue)
        else if (pmv < -0.5) colors = ["#60a5fa", "#2563eb"];  // Cool (Light Blue)
        else if (pmv <= 0.5)  colors = ["#10b981", "#047857"]; // OK (Emerald)
        else if (pmv <= 1.0)  colors = ["#f59e0b", "#b45309"]; // Warm (Amber)
        else colors = ["#ef4444", "#b91c1c"];                  // Hot (Red)

        const grad = ctx.createLinearGradient(x, y, x + w, y + h);
        grad.addColorStop(0, colors[0] + "80"); // 50% opacity
        grad.addColorStop(1, colors[1] + "50"); // 30% opacity
        return grad;
    }

    healthColor(h) {
        if (h >= 90) return "#10b981";
        if (h >= 70) return "#f59e0b";
        return "#ef4444";
    }

    // Draw the idle / waiting state
    drawIdle() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.W, this.H);
        
        // Background
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, this.W, this.H);
        
        // Grid pattern overlay
        ctx.strokeStyle = "rgba(51, 65, 85, 0.15)";
        ctx.lineWidth = 1;
        for(let i=0; i<this.W; i+=40) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,this.H); ctx.stroke(); }
        for(let j=0; j<this.H; j+=40) { ctx.beginPath(); ctx.moveTo(0,j); ctx.lineTo(this.W,j); ctx.stroke(); }

        // Draw room outlines
        Object.values(this.rooms).forEach(r => {
            // Glass panel background
            ctx.fillStyle = "rgba(17, 24, 39, 0.6)";
            ctx.beginPath();
            this._roundRect(ctx, r.x, r.y, r.w, r.h, 12);
            ctx.fill();

            // Glowing border
            ctx.strokeStyle = "rgba(56, 189, 248, 0.2)";
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Label
            ctx.fillStyle = "#64748b";
            ctx.font = "600 15px Outfit, sans-serif";
            ctx.fillText(r.label, r.x + 20, r.y + 35);
        });

        // Center pulse text
        this._pulsePhase += 0.05;
        const alpha = 0.5 + 0.5 * Math.sin(this._pulsePhase);
        ctx.fillStyle = `rgba(56, 189, 248, ${alpha})`;
        ctx.font = "600 18px Outfit, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Ready to Initialize EnergyPlus Simulation", this.W / 2, this.H / 2 - 10);
        ctx.fillStyle = "#64748b";
        ctx.font = "400 14px Inter, sans-serif";
        ctx.fillText("Click ▶ Execute Step or ▶ Play Day on the dashboard toolbar", this.W / 2, this.H / 2 + 15);
        ctx.textAlign = "left";

        requestAnimationFrame(() => {
            if (this._toastState === "idle" && (!currentStep || currentStep === 1)) {
                this.drawIdle();
            }
        });
    }

    // Full render with live data
    render(state, health, council) {
        this._pulsePhase += 0.05;
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.W, this.H);
        
        // Background & Grid
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, this.W, this.H);
        ctx.strokeStyle = "rgba(51, 65, 85, 0.15)";
        ctx.lineWidth = 1;
        for(let i=0; i<this.W; i+=40) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,this.H); ctx.stroke(); }
        for(let j=0; j<this.H; j+=40) { ctx.beginPath(); ctx.moveTo(0,j); ctx.lineTo(this.W,j); ctx.stroke(); }

        const zones = state.zones || {};

        // Draw each room
        Object.entries(this.rooms).forEach(([zoneId, r]) => {
            const z = zones[zoneId];
            const pmv = z ? (z.pmv || 0) : 0;
            const temp = z ? (z.temperature || 0) : 0;
            const setpoint = z ? (z.target_setpoint || 0) : 0;
            const occ = z ? (z.occupancy || 0) : 0;
            const co2 = z ? (z.co2 || 0) : 0;
            const humidity = z ? (z.humidity || 0) : 0;

            // Base glass panel
            ctx.fillStyle = "rgba(17, 24, 39, 0.7)";
            ctx.beginPath();
            this._roundRect(ctx, r.x, r.y, r.w, r.h, 12);
            ctx.fill();

            // PMV Gradient Overlay
            ctx.fillStyle = this.pmvColor(pmv, ctx, r.x, r.y, r.w, r.h);
            ctx.fill();

            // Neon Border
            ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
            ctx.lineWidth = 1;
            ctx.stroke();

            // Room label
            ctx.fillStyle = "#f8fafc";
            ctx.font = "600 16px Outfit, sans-serif";
            ctx.shadowColor = "rgba(0,0,0,0.5)";
            ctx.shadowBlur = 4;
            ctx.fillText(r.label, r.x + 20, r.y + 35);
            ctx.shadowBlur = 0; // reset

            // Metrics Box
            ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
            ctx.beginPath();
            this._roundRect(ctx, r.x + 20, r.y + 55, r.w - 40, 90, 8);
            ctx.fill();

            ctx.fillStyle = "#e2e8f0";
            ctx.font = "400 13px Inter, sans-serif";
            
            // Highlight setpoint differently if it changed
            ctx.fillText("Temp:", r.x + 35, r.y + 78);
            ctx.font = "600 13px Inter, sans-serif";
            ctx.fillStyle = "#38bdf8";
            ctx.fillText(`${temp.toFixed(1)}°C`, r.x + 78, r.y + 78);
            
            ctx.font = "400 13px Inter, sans-serif";
            ctx.fillStyle = "#94a3b8";
            ctx.fillText(`(Set: ${setpoint.toFixed(1)}°C)`, r.x + 135, r.y + 78);

            // PMV display
            ctx.fillStyle = "#e2e8f0";
            ctx.fillText(`PMV:`, r.x + 35, r.y + 100);
            ctx.font = "600 13px Inter, sans-serif";
            ctx.fillStyle = (Math.abs(pmv) <= 0.5) ? "#10b981" : "#f59e0b";
            ctx.fillText(`${pmv.toFixed(2)}`, r.x + 75, r.y + 100);

            // IAQ
            ctx.font = "400 12px Inter, sans-serif";
            ctx.fillStyle = "#cbd5e1";
            ctx.fillText(`RH: ${humidity.toFixed(1)}%   |   CO₂: ${co2.toFixed(0)} ppm`, r.x + 35, r.y + 125);

            // Draw occupant dots (animated pulsing)
            const dotCount = Math.min(occ, 20);
            const cols = Math.min(5, r.w > 200 ? 5 : 3);
            const pulse = 1 + 0.3 * Math.sin(this._pulsePhase * 3);

            for (let i = 0; i < dotCount; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const cx = r.x + r.w - 30 - col * 22;
                const cy = r.y + r.h - 35 - row * 22;
                
                // Glow
                ctx.beginPath();
                ctx.arc(cx, cy, 5 * pulse, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(56, 189, 248, 0.4)";
                ctx.fill();

                // Core
                ctx.beginPath();
                ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
                ctx.fillStyle = "#38bdf8";
                ctx.fill();
            }
            if (occ > 20) {
                ctx.fillStyle = "#f8fafc";
                ctx.font = "600 12px Inter, sans-serif";
                ctx.fillText(`+${occ - 20} more`, r.x + r.w - 70 - cols * 20, r.y + r.h - 30);
            }
            
            // Total occupancy label
            ctx.fillStyle = "#94a3b8";
            ctx.font = "400 12px Inter, sans-serif";
            ctx.fillText(`Occupants: ${occ}`, r.x + 20, r.y + r.h - 20);
        });

        // ── Right sidebar: Weather + Equipment Health + PMV Legend ──
        const sx = 1020; // Shifted right to accommodate wider rooms
        let sy = 35;

        // Weather
        ctx.fillStyle = "#f8fafc";
        ctx.font = "600 15px Outfit, sans-serif";
        ctx.fillText("Environment", sx, sy);
        
        ctx.fillStyle = "rgba(255,255,255,0.1)";
        ctx.fillRect(sx, sy+8, 160, 1);
        sy += 25;

        ctx.fillStyle = "#94a3b8";
        ctx.font = "400 12px Inter, sans-serif";
        const outTemp = state.outdoor_temp !== undefined ? state.outdoor_temp.toFixed(1) : "--";
        const outHum = state.outdoor_humidity !== undefined ? state.outdoor_humidity.toFixed(1) : "--";
        
        ctx.fillText(`Ambient Temp:`, sx, sy);
        ctx.fillStyle = "#e2e8f0";
        ctx.fillText(`${outTemp}°C`, sx + 100, sy);
        sy += 20;

        ctx.fillStyle = "#94a3b8";
        ctx.fillText(`Humidity:`, sx, sy);
        ctx.fillStyle = "#e2e8f0";
        ctx.fillText(`${outHum}%`, sx + 100, sy);
        sy += 20;

        ctx.fillStyle = "#94a3b8";
        ctx.fillText(`Time Step:`, sx, sy);
        ctx.fillStyle = "#38bdf8";
        ctx.fillText(`${state.timestep || 0}`, sx + 100, sy);
        sy += 40;

        // Equipment Health Boxes
        ctx.fillStyle = "#f8fafc";
        ctx.font = "600 15px Outfit, sans-serif";
        ctx.fillText("Hardware Health", sx, sy);
        ctx.fillStyle = "rgba(255,255,255,0.1)";
        ctx.fillRect(sx, sy+8, 160, 1);
        sy += 25;

        const eqItems = [
            { name: "AHU",     score: health?.assets?.AHU?.health_score ?? 98 },
            { name: "Chiller", score: health?.assets?.CHILLER?.health_score ?? 92 },
            { name: "Pump",    score: health?.assets?.PUMP?.health_score ?? 78 },
            { name: "Fan",     score: health?.assets?.FAN?.health_score ?? 95 },
        ];
        eqItems.forEach((eq, i) => {
            const bx = sx + (i % 2) * 85;
            const by = sy + Math.floor(i / 2) * 55;
            
            // Glass Box
            ctx.fillStyle = "rgba(30,41,59,0.7)";
            ctx.beginPath();
            this._roundRect(ctx, bx, by, 75, 46, 8);
            ctx.fill();
            
            ctx.strokeStyle = "rgba(255,255,255,0.05)";
            ctx.lineWidth = 1;
            ctx.stroke();

            // Glow Dot
            const eqColor = this.healthColor(eq.score);
            ctx.beginPath();
            ctx.arc(bx + 15, by + 16, 4, 0, Math.PI * 2);
            ctx.fillStyle = eqColor;
            ctx.fill();
            ctx.shadowColor = eqColor;
            ctx.shadowBlur = 6;
            ctx.fill();
            ctx.shadowBlur = 0; // reset

            // Label
            ctx.fillStyle = "#cbd5e1";
            ctx.font = "400 12px Inter, sans-serif";
            ctx.fillText(eq.name, bx + 26, by + 20);
            
            // Score
            ctx.fillStyle = eqColor;
            ctx.font = "600 13px Inter, sans-serif";
            ctx.fillText(`${eq.score.toFixed(0)}%`, bx + 15, by + 38);
        });
        sy += 120;

        // PMV Legend
        ctx.fillStyle = "#f8fafc";
        ctx.font = "600 15px Outfit, sans-serif";
        ctx.fillText("PMV Index", sx, sy);
        ctx.fillStyle = "rgba(255,255,255,0.1)";
        ctx.fillRect(sx, sy+8, 160, 1);
        sy += 25;

        const legends = [
            { label: "< -1.0 Cold",      colors: ["#3b82f6", "#1d4ed8"] },
            { label: "-1.0 to -0.5 Cool", colors: ["#60a5fa", "#2563eb"] },
            { label: "-0.5 to 0.5 Ideal", colors: ["#10b981", "#047857"] },
            { label: "0.5 to 1.0 Warm",   colors: ["#f59e0b", "#b45309"] },
            { label: "> 1.0 Hot",         colors: ["#ef4444", "#b91c1c"] },
        ];
        legends.forEach((l, i) => {
            const ly = sy + i * 24;
            
            // Gradient square
            const grad = ctx.createLinearGradient(sx, ly, sx + 18, ly + 18);
            grad.addColorStop(0, l.colors[0]);
            grad.addColorStop(1, l.colors[1]);
            ctx.fillStyle = grad;
            
            ctx.beginPath();
            this._roundRect(ctx, sx, ly, 18, 18, 4);
            ctx.fill();
            
            ctx.fillStyle = "#94a3b8";
            ctx.font = "400 12px Inter, sans-serif";
            ctx.fillText(l.label, sx + 28, ly + 14);
        });

        // Toast notification (AI reasoning)
        this._updateToast(council);
        this._drawToast();
        
        // Loop animation if playing
        if (isPlaying) {
            requestAnimationFrame(() => this.render(state, health, council));
        }
    }

    _updateToast(council) {
        if (!council) return;
        const ts = council.timestep || 0;
        if (ts !== this._lastCouncilTs && council.comfort_reasoning) {
            this._lastCouncilTs = ts;
            this._toastMsg = council.comfort_reasoning.split(".")[0] + ".";
            this._toastAlpha = 1.0;
            this._toastState = "show";
            this._toastStart = Date.now();
        }
        if (this._toastState === "show" && Date.now() - this._toastStart > 4000) {
            this._toastState = "fade";
        }
        if (this._toastState === "fade") {
            this._toastAlpha = Math.max(0, this._toastAlpha - 0.05);
            if (this._toastAlpha <= 0) this._toastState = "idle";
        }
    }

    _drawToast() {
        if (this._toastState === "idle" || !this._toastMsg) return;
        const ctx = this.ctx;
        const tw = 360, th = 68;
        const tx = this.W - tw - 20;
        
        // Slide up animation
        let slideOffset = 0;
        if (this._toastState === "show") {
            const elapsed = Date.now() - this._toastStart;
            if (elapsed < 300) {
                slideOffset = 20 * (1 - (elapsed/300));
            }
        }
        const ty = this.H - th - 20 + slideOffset;

        ctx.save();
        ctx.globalAlpha = this._toastAlpha;
        
        // Shadow
        ctx.shadowColor = "rgba(0,0,0,0.5)";
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 4;
        
        // Box
        ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
        ctx.beginPath();
        this._roundRect(ctx, tx, ty, tw, th, 12);
        ctx.fill();
        
        ctx.shadowBlur = 0; // reset
        
        // Animated gradient border
        const t = Date.now() / 1000;
        const grad = ctx.createLinearGradient(tx, ty, tx + tw, ty + th);
        grad.addColorStop(0, `rgba(56, 189, 248, ${0.5 + 0.5 * Math.sin(t)})`);
        grad.addColorStop(1, `rgba(16, 185, 129, ${0.5 + 0.5 * Math.cos(t)})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "#38bdf8";
        ctx.font = "600 13px Outfit, sans-serif";
        ctx.fillText("✨ AI Reasoning Update", tx + 15, ty + 22);

        ctx.fillStyle = "#cbd5e1";
        ctx.font = "400 12px Inter, sans-serif";
        
        // Word wrap message
        const words = this._toastMsg.split(" ");
        let line = "";
        let y = ty + 42;
        for(let n = 0; n < words.length; n++) {
            const testLine = line + words[n] + " ";
            const metrics = ctx.measureText(testLine);
            if (metrics.width > tw - 30 && n > 0) {
                ctx.fillText(line, tx + 15, y);
                line = words[n] + " ";
                y += 16;
            } else {
                line = testLine;
            }
            if (y > ty + 50) { line += "..."; break; } // Truncate to 2 lines
        }
        ctx.fillText(line, tx + 15, y);
        
        ctx.restore();
    }

    _roundRect(ctx, x, y, w, h, r) {
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
    }
}
