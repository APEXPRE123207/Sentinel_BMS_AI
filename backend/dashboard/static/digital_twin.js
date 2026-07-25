/**
 * Phase 6: Interactive Digital Twin
 * Handles both SVG and Three.js rendering of the building state.
 */

// UI Elements
const btnToggleRenderer = document.getElementById("btn-toggle-renderer");
const svgContainer = document.getElementById("twin-svg");
const svgRoomsGroup = document.getElementById("svg-rooms");
const threeContainer = document.getElementById("twin-3d");
const equipmentOverlay = document.getElementById("twin-equipment-overlay");
const sidePanel = document.getElementById("twin-side-panel");
const btnClosePanel = document.getElementById("btn-close-panel");

let currentRenderer = "SVG"; // "SVG" or "3D"
let currentRoomStates = [];
let currentEquipmentStates = [];

// Room Layout Definition (2D and 3D mapping)
const ROOM_LAYOUTS = {
    "Office": { w: 150, h: 100, x: 0, y: 0 },
    "ConferenceRoom": { w: 150, h: 100, x: 160, y: 0 },
    "Lobby": { w: 310, h: 100, x: 0, y: 110 }
};

// Temp Color Scale
function getTempColor(temp) {
    if (temp < 21) return "#3b82f6"; // Blue
    if (temp <= 24) return "#22c55e"; // Green
    return "#ef4444"; // Red
}

// Side Panel Logic
function openSidePanel(roomData) {
    document.getElementById("panel-room-name").textContent = roomData.name || roomData.id;
    document.getElementById("panel-temp").textContent = roomData.temp ? roomData.temp.toFixed(1) : "--";
    document.getElementById("panel-target").textContent = roomData.target_setpoint ? roomData.target_setpoint.toFixed(1) : "--";
    document.getElementById("panel-humidity").textContent = roomData.humidity ? roomData.humidity.toFixed(1) : "--";
    document.getElementById("panel-occ").textContent = roomData.occupancy !== undefined ? roomData.occupancy : "--";
    document.getElementById("panel-pmv").textContent = roomData.pmv ? roomData.pmv.toFixed(2) : "--";
    document.getElementById("panel-airflow").textContent = roomData.airflow ? roomData.airflow.toFixed(2) : "--";
    
    sidePanel.style.display = "flex";
}

btnClosePanel.addEventListener("click", () => {
    sidePanel.style.display = "none";
});

// ==========================================
// Step 0: SVG Renderer
// ==========================================
function renderSVG(roomStates) {
    svgRoomsGroup.innerHTML = "";
    
    roomStates.forEach(room => {
        const layout = ROOM_LAYOUTS[room.id];
        if (!layout) return;
        
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", layout.x);
        rect.setAttribute("y", layout.y);
        rect.setAttribute("width", layout.w);
        rect.setAttribute("height", layout.h);
        rect.setAttribute("fill", getTempColor(room.temp));
        rect.setAttribute("stroke", "#0f172a");
        rect.setAttribute("stroke-width", "2");
        rect.style.cursor = "pointer";
        rect.style.transition = "fill 0.3s ease";
        
        // Hover effects
        rect.addEventListener("mouseenter", () => rect.setAttribute("stroke", "#38bdf8"));
        rect.addEventListener("mouseleave", () => rect.setAttribute("stroke", "#0f172a"));
        
        // Click interaction
        rect.addEventListener("click", () => {
            openSidePanel(room);
        });
        
        // Label
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", layout.x + layout.w / 2);
        text.setAttribute("y", layout.y + layout.h / 2);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dominant-baseline", "middle");
        text.setAttribute("fill", "#ffffff");
        text.setAttribute("font-size", "12");
        text.setAttribute("font-family", "Inter, sans-serif");
        text.style.pointerEvents = "none";
        text.textContent = room.name || room.id;
        
        svgRoomsGroup.appendChild(rect);
        svgRoomsGroup.appendChild(text);
    });
}

// Mock Test Initializer
function testSVG() {
    const mockRooms = [
        { id: "Office", name: "Main Office", temp: 22.5, humidity: 45, occupancy: 8, pmv: 0.1, target_setpoint: 22.0, airflow: 0.5 },
        { id: "ConferenceRoom", name: "Conference Room", temp: 25.1, humidity: 55, occupancy: 15, pmv: 1.2, target_setpoint: 22.0, airflow: 1.0 },
        { id: "Lobby", name: "Entrance Lobby", temp: 19.5, humidity: 40, occupancy: 2, pmv: -1.5, target_setpoint: 21.0, airflow: 0.2 }
    ];
    renderSVG(mockRooms);
}

// Initialize Step 0 automatically for testing
testSVG();

// ==========================================
// Step 1 & 2: Three.js Base Scene & Interaction
// ==========================================
let scene, camera, renderer, raycaster, mouse;
let roomMeshes = {};

function initThreeJS() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a); // match panel background
    
    // Isometric Orthographic Camera
    const aspect = threeContainer.clientWidth / threeContainer.clientHeight;
    const frustumSize = 400;
    camera = new THREE.OrthographicCamera(
        frustumSize * aspect / -2, frustumSize * aspect / 2,
        frustumSize / 2, frustumSize / -2,
        1, 1000
    );
    
    // Isometric angle: Look at origin from an angle
    camera.position.set(200, 300, 200);
    camera.lookAt(0, 0, 0);
    
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(threeContainer.clientWidth, threeContainer.clientHeight);
    threeContainer.appendChild(renderer.domElement);
    
    // Create Room Meshes
    // Map SVG coordinates to 3D center coordinates.
    // SVG total bounds: 310 width (x), 210 height (y). Center is (155, 105).
    const centerX = 155;
    const centerY = 105;
    
    for (const [roomId, layout] of Object.entries(ROOM_LAYOUTS)) {
        const geometry = new THREE.BoxGeometry(layout.w, 40, layout.h);
        
        // Use edges geometry to recreate the stroke effect
        const edges = new THREE.EdgesGeometry(geometry);
        const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x0f172a, linewidth: 2 }));
        
        const material = new THREE.MeshBasicMaterial({ color: 0x3b82f6 }); // default blue
        const mesh = new THREE.Mesh(geometry, material);
        
        // Position relative to center
        mesh.position.set(layout.x + layout.w/2 - centerX, 0, layout.y + layout.h/2 - centerY);
        line.position.copy(mesh.position);
        
        mesh.userData = { roomId: roomId };
        
        scene.add(mesh);
        scene.add(line);
        roomMeshes[roomId] = mesh;
    }
    
    // Step 2: Raycaster for Click Interaction
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    
    renderer.domElement.addEventListener("click", onThreeClick, false);
    
    window.addEventListener("resize", onWindowResize, false);
    
    animate();
}

function onWindowResize() {
    if (!renderer) return;
    const aspect = threeContainer.clientWidth / threeContainer.clientHeight;
    const frustumSize = 400;
    camera.left = frustumSize * aspect / -2;
    camera.right = frustumSize * aspect / 2;
    camera.top = frustumSize / 2;
    camera.bottom = frustumSize / -2;
    camera.updateProjectionMatrix();
    renderer.setSize(threeContainer.clientWidth, threeContainer.clientHeight);
}

function onThreeClick(event) {
    if (currentRenderer !== "3D") return;
    
    // Calculate mouse position in normalized device coordinates (-1 to +1)
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(Object.values(roomMeshes));
    
    if (intersects.length > 0) {
        const roomId = intersects[0].object.userData.roomId;
        const roomData = currentRoomStates.find(r => r.id === roomId);
        if (roomData) {
            openSidePanel(roomData);
        }
    }
}

function renderThreeJS(roomStates) {
    if (!renderer) initThreeJS();
    
    roomStates.forEach(room => {
        const mesh = roomMeshes[room.id];
        if (mesh) {
            mesh.material.color.set(getTempColor(room.temp));
        }
    });
}

function animate() {
    requestAnimationFrame(animate);
    if (currentRenderer === "3D" && renderer) {
        renderer.render(scene, camera);
        updateEquipmentOverlay(); // From Step 3
    }
}

const EQUIPMENT_LAYOUTS = {
    "AHU": { x: -80, y: 30, z: -80 },
    "CHILLER": { x: -30, y: 30, z: -80 },
    "PUMP": { x: 20, y: 30, z: -80 },
    "FAN": { x: 70, y: 30, z: -80 }
};

const EQUIPMENT_SVG_POSITIONS = {
    "AHU": { x: 30, y: -20 },
    "CHILLER": { x: 90, y: -20 },
    "PUMP": { x: 150, y: -20 },
    "FAN": { x: 210, y: -20 }
};

let equipMarkers3D = {};

function initEquipment3D() {
    for (const [eqId, pos] of Object.entries(EQUIPMENT_LAYOUTS)) {
        const geo = new THREE.BoxGeometry(10, 10, 10);
        const mat = new THREE.MeshBasicMaterial({ color: 0x64748b });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(pos.x, pos.y, pos.z);
        scene.add(mesh);
        equipMarkers3D[eqId] = mesh;
    }
}

// Ensure it's called during initThreeJS
// (We will hook this up by overwriting initThreeJS partially later, or just call it here)
// Actually we can just redefine initThreeJS or call it now since scene is global.

function getHealthColor(healthPct) {
    if (healthPct > 85) return "#10b981"; // green
    if (healthPct > 60) return "#f59e0b"; // amber
    return "#ef4444"; // red
}

function updateEquipmentOverlay() {
    equipmentOverlay.innerHTML = "";
    
    currentEquipmentStates.forEach(eq => {
        let screenX, screenY;
        
        if (currentRenderer === "3D" && camera) {
            const mesh = equipMarkers3D[eq.id];
            if (!mesh) return;
            const vector = new THREE.Vector3();
            vector.setFromMatrixPosition(mesh.matrixWorld);
            vector.project(camera);
            
            const halfWidth = threeContainer.clientWidth / 2;
            const halfHeight = threeContainer.clientHeight / 2;
            
            screenX = (vector.x * halfWidth) + halfWidth;
            screenY = -(vector.y * halfHeight) + halfHeight;
        } else {
            // SVG mode fallback
            const pos = EQUIPMENT_SVG_POSITIONS[eq.id];
            if (!pos) return;
            // Translate SVG coordinates to container coordinates
            screenX = pos.x + 50; // SVG translate(50,50)
            screenY = pos.y + 50;
        }
        
        const dot = document.createElement("div");
        dot.style.position = "absolute";
        dot.style.left = `${screenX - 8}px`;
        dot.style.top = `${screenY - 8}px`;
        dot.style.width = "16px";
        dot.style.height = "16px";
        dot.style.borderRadius = "50%";
        dot.style.backgroundColor = getHealthColor(eq.healthPct);
        dot.style.border = "2px solid #0f172a";
        dot.style.boxShadow = "0 0 8px rgba(0,0,0,0.5)";
        dot.title = `${eq.name}: ${eq.status} (${eq.healthPct}%)`;
        
        equipmentOverlay.appendChild(dot);
    });
}

// ==========================================
// Steps 4 & 5: Real Data & Playback Toggle
// ==========================================

window.updateDigitalTwin = function(state, health) {
    if (!state || !state.zones) return;
    
    currentRoomStates = Object.keys(state.zones).map(zoneId => {
        const z = state.zones[zoneId];
        return {
            id: zoneId,
            name: zoneId.replace(/([A-Z])/g, ' $1').trim(),
            temp: z.temperature,
            target_setpoint: z.target_setpoint,
            humidity: z.humidity,
            occupancy: z.occupancy,
            pmv: z.pmv,
            airflow: z.airflow
        };
    });
    
    if (health && health.assets) {
        currentEquipmentStates = Object.keys(health.assets).map(eqId => {
            const eq = health.assets[eqId];
            return {
                id: eqId,
                name: eqId,
                healthPct: eq.health_score,
                status: eq.status
            };
        });
    }
    
    if (currentRenderer === "SVG") {
        renderSVG(currentRoomStates);
        updateEquipmentOverlay();
    } else {
        renderThreeJS(currentRoomStates);
    }
    
    // Auto-update side panel if open
    const openRoomName = document.getElementById("panel-room-name").textContent;
    const activeRoom = currentRoomStates.find(r => (r.name || r.id) === openRoomName);
    if (activeRoom && sidePanel.style.display !== "none") {
        openSidePanel(activeRoom);
    }
};

btnToggleRenderer.addEventListener("click", () => {
    if (currentRenderer === "SVG") {
        currentRenderer = "3D";
        svgContainer.style.display = "none";
        threeContainer.style.display = "block";
        btnToggleRenderer.textContent = "Switch to SVG View";
        renderThreeJS(currentRoomStates);
    } else {
        currentRenderer = "SVG";
        threeContainer.style.display = "none";
        svgContainer.style.display = "block";
        btnToggleRenderer.textContent = "Switch to 3D View";
        renderSVG(currentRoomStates);
        updateEquipmentOverlay();
    }
});

initEquipment3D();
