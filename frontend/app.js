/**
 * RadioCov - Pure RF Spectrum Coverage & 1,000-ft Airspace Cube Frontend Logic
 */

let map = null;
let txMarker = null;
let rangeCirclesGroup = null;
let coveragePolygonLayer = null;
let radialLineLayer = null;

let currentPresets = null;
let activeHorizontalData = null;
let activeRadialData = null;
let activeVolumetricData = null;

// Three.js 3D variables
let threeScene = null;
let threeCamera = null;
let threeRenderer = null;
let threeControls = null;
let threeCubeGroup = null;
let threeZScale = 5.0;

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initThreeJs();
  populateTechnologySelectors();
  loadPresets();
  setupCanvasInteractions();

  // Initial calculation
  setTimeout(() => calculateCoverage(), 400);
});

/* =========================================================================
   1. MAP INITIALIZATION (2D VIEW)
   ========================================================================= */
function initMap() {
  const mapEl = document.getElementById("mapContainer");
  if (!mapEl) return;

  const initLat = parseFloat(document.getElementById("txLat").value) || 47.4211;
  const initLon = parseFloat(document.getElementById("txLon").value) || 10.9853;

  map = L.map("mapContainer", {
    center: [initLat, initLon],
    zoom: 8,
    zoomControl: true
  });

  // Base tile layers (100% Free, NO API KEY required, NO watermarks)
  const esriDark = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxZoom: 16
  });

  const osmStandard = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  });

  const esriTopo = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
    attribution: 'Tiles &copy; Esri &mdash; National Geographic, DeLorme, NAVTEQ',
    maxZoom: 18
  });

  const esriSatellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 18
  });

  // Default to sleek Dark Gray
  esriDark.addTo(map);

  // Basemap switcher
  const baseMaps = {
    "Dark Gray (No Key)": esriDark,
    "OpenStreetMap (Standard)": osmStandard,
    "Topographic": esriTopo,
    "Satellite Imagery": esriSatellite
  };
  L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

  rangeCirclesGroup = L.layerGroup().addTo(map);

  // Transmitter marker (draggable)
  const txIcon = L.divIcon({
    className: "tx-custom-icon",
    html: '<div style="background:#38bdf8; width:16px; height:16px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 10px #38bdf8;"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });

  txMarker = L.marker([initLat, initLon], { icon: txIcon, draggable: true }).addTo(map);
  txMarker.bindTooltip("<b>Transmitter (Tx)</b>", { permanent: false, direction: "top" });

  txMarker.on("dragend", (e) => {
    const pos = e.target.getLatLng();
    document.getElementById("txLat").value = pos.lat.toFixed(4);
    document.getElementById("txLon").value = pos.lng.toFixed(4);
    calculateCoverage();
  });

  // Click on map to place transmitter
  map.on("click", (e) => {
    txMarker.setLatLng(e.latlng);
    document.getElementById("txLat").value = e.latlng.lat.toFixed(4);
    document.getElementById("txLon").value = e.latlng.lng.toFixed(4);
    calculateCoverage();
  });
}

function updateMapLayers() {
  if (!map || !txMarker) return;
  const lat = parseFloat(document.getElementById("txLat").value);
  const lon = parseFloat(document.getElementById("txLon").value);
  const rangeKm = parseFloat(document.getElementById("rangeKm").value);

  txMarker.setLatLng([lat, lon]);

  // Update range rings with small numbering labels
  rangeCirclesGroup.clearLayers();
  const ringStep = rangeKm > 100 ? 50 : 25;
  const bearing = parseFloat(document.getElementById("radialBearing").value) || 0;

  // Choose an azimuth for distance labels that doesn't collide with the radial indicator line
  let labelBearing = 0; // Due North
  if (Math.abs(bearing - 0) < 20 || Math.abs(bearing - 360) < 20) {
    labelBearing = 90; // Due East if radial is pointing North
  }

  const ringList = [];
  for (let r = ringStep; r <= rangeKm; r += ringStep) {
    ringList.push(r);
  }
  if (!ringList.includes(rangeKm) && rangeKm > 10) {
    ringList.push(rangeKm);
  }

  ringList.forEach(r => {
    // 1. Draw range circle
    L.circle([lat, lon], {
      radius: r * 1000,
      color: "rgba(56, 189, 248, 0.28)",
      weight: r === rangeKm ? 1.5 : 1,
      dashArray: "4, 4",
      fill: false,
      interactive: false
    }).addTo(rangeCirclesGroup);

    // 2. Add small numbering label along ring perimeter
    const labelPos = destinationPoint(lat, lon, labelBearing, r * 1000);
    const ringLabelIcon = L.divIcon({
      className: "range-ring-div-icon",
      html: `<div class="range-ring-badge">${r} km</div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    });

    L.marker([labelPos.lat, labelPos.lon], {
      icon: ringLabelIcon,
      interactive: false
    }).addTo(rangeCirclesGroup);
  });

  // Draw radial indicator line
  const destLatLon = destinationPoint(lat, lon, bearing, rangeKm * 1000);
  if (radialLineLayer) map.removeLayer(radialLineLayer);
  radialLineLayer = L.polyline([[lat, lon], [destLatLon.lat, destLatLon.lon]], {
    color: "#f59e0b",
    weight: 2,
    dashArray: "5, 5"
  }).addTo(map);
  radialLineLayer.bindTooltip(`Radial ${Math.round(bearing)}°`, { sticky: true });
}

/* =========================================================================
   2. THREE.JS INITIALIZATION (3D VOLUMETRIC VIEW)
   ========================================================================= */
function initThreeJs() {
  const container = document.getElementById("threeContainer");
  if (!container || !window.THREE) return;

  const w = container.clientWidth || 800;
  const h = container.clientHeight || 600;

  threeScene = new THREE.Scene();
  threeScene.background = new THREE.Color(0x050811);

  threeCamera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
  // Crucial: Set Z-axis as the vertical UP axis (Altitude AMSL)
  threeCamera.up.set(0, 0, 1);
  threeCamera.position.set(0, -130, 80);
  threeCamera.lookAt(0, 0, 5);

  threeRenderer = new THREE.WebGLRenderer({ antialias: true });
  threeRenderer.setSize(w, h);
  threeRenderer.setPixelRatio(window.devicePixelRatio || 1);
  container.appendChild(threeRenderer.domElement);

  if (window.THREE.OrbitControls) {
    threeControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
    threeControls.target.set(0, 0, 5);
    threeControls.enableDamping = true;
    threeControls.dampingFactor = 0.05;
    threeControls.minDistance = 5;
    threeControls.maxDistance = 1000;
    // Keep camera right-side up: allow from top-down (0.05 rad) to horizon (PI/2 rad)
    threeControls.minPolarAngle = 0.05;
    threeControls.maxPolarAngle = Math.PI / 2 - 0.02;
    threeControls.update();
  }

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  threeScene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(50, 50, 100);
  threeScene.add(dirLight);

  // Ground Grid
  const gridHelper = new THREE.GridHelper(200, 20, 0x334155, 0x1e293b);
  gridHelper.rotation.x = Math.PI / 2;
  threeScene.add(gridHelper);

  // Tx Marker in 3D
  const txGeo = new THREE.SphereGeometry(1.5, 16, 16);
  const txMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
  const txMesh = new THREE.Mesh(txGeo, txMat);
  txMesh.position.set(0, 0, 0);
  threeScene.add(txMesh);

  threeCubeGroup = new THREE.Group();
  threeScene.add(threeCubeGroup);

  // 3D In-Scene North Marker & Compass
  const northMarker = createNorthMarker();
  threeScene.add(northMarker);

  window.addEventListener("resize", onWindowResize);
  animateThree();
}

function onWindowResize() {
  const container = document.getElementById("threeContainer");
  if (!container || !threeCamera || !threeRenderer) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  threeCamera.aspect = w / h;
  threeCamera.updateProjectionMatrix();
  threeRenderer.setSize(w, h);
}

function animateThree() {
  requestAnimationFrame(animateThree);
  if (threeControls) threeControls.update();
  updateCompassHUD();
  if (threeRenderer && threeScene && threeCamera) {
    threeRenderer.render(threeScene, threeCamera);
  }
}

function createNorthMarker() {
  const northGroup = new THREE.Group();
  northGroup.name = "northMarkerGroup";

  const origin = new THREE.Vector3(0, 0, 0.15); // Slightly above ground grid

  // 1. Prominent Red 3D Arrow pointing due North (+Y)
  const dirNorth = new THREE.Vector3(0, 1, 0);
  const northLength = 60;
  const arrowNorth = new THREE.ArrowHelper(dirNorth, origin, northLength, 0xef4444, 10, 6);
  northGroup.add(arrowNorth);

  // 2. Cyan Arrow pointing due East (+X)
  const dirEast = new THREE.Vector3(1, 0, 0);
  const eastLength = 40;
  const arrowEast = new THREE.ArrowHelper(dirEast, origin, eastLength, 0x38bdf8, 6, 3.5);
  northGroup.add(arrowEast);

  // 3. Subdued Axis Lines for South (-Y) and West (-X)
  const dirSouth = new THREE.Vector3(0, -1, 0);
  const arrowSouth = new THREE.ArrowHelper(dirSouth, origin, 30, 0x475569, 4, 2.5);
  northGroup.add(arrowSouth);

  const dirWest = new THREE.Vector3(-1, 0, 0);
  const arrowWest = new THREE.ArrowHelper(dirWest, origin, 30, 0x475569, 4, 2.5);
  northGroup.add(arrowWest);

  // 4. Subtle Ground Compass Range Ring (Radius 50 km)
  const ringGeo = new THREE.RingGeometry(49.6, 50.4, 64);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, opacity: 0.25, transparent: true });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  northGroup.add(ringMesh);

  // 5. Billboard Text Sprite Helper
  function createTextSprite(text, bgColor, textColor, size = 128) {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();

    ctx.fillStyle = textColor;
    ctx.font = `bold ${Math.round(size * 0.52)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, size / 2, size / 2 + 2);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, depthTest: false });
    const sprite = new THREE.Sprite(spriteMat);
    return sprite;
  }

  // North "N" Billboard Sprite at (0, 68, 3)
  const northSprite = createTextSprite("N", "#ef4444", "#ffffff");
  northSprite.position.set(0, northLength + 8, 3.0);
  northSprite.scale.set(11, 11, 1);
  northGroup.add(northSprite);

  // East "E" Billboard Sprite at (46, 0, 2)
  const eastSprite = createTextSprite("E", "#0284c7", "#ffffff");
  eastSprite.position.set(eastLength + 6, 0, 2.0);
  eastSprite.scale.set(8, 8, 1);
  northGroup.add(eastSprite);

  return northGroup;
}

function updateCompassHUD() {
  if (!threeCamera) return;
  const needle = document.getElementById("compassNeedle");
  if (!needle) return;

  const dir = new THREE.Vector3();
  threeCamera.getWorldDirection(dir);
  // Ground plane: +Y is North, +X is East
  const angleRad = Math.atan2(dir.x, dir.y);
  const angleDeg = (angleRad * 180.0) / Math.PI;

  needle.style.transform = `rotate(${-angleDeg}deg)`;
}

function updateThreeZScale(val) {
  threeZScale = parseFloat(val) || 5.0;
  if (threeCubeGroup) {
    threeCubeGroup.scale.set(1.0, 1.0, threeZScale);
  }
}

function resetThreeView() {
  if (!threeCamera || !threeControls) return;
  threeCamera.up.set(0, 0, 1);
  threeCamera.position.set(0, -130, 80);
  threeControls.target.set(0, 0, 5);
  threeCamera.lookAt(0, 0, 5);
  threeControls.update();
}

let current3DPoints = null;
let threeMaxAltFilter = Infinity;

function onThreeMaxAltChange(val) {
  threeMaxAltFilter = parseInt(val, 10);
  const label = document.getElementById("threeMaxAltLabel");
  if (label) {
    label.textContent = `${threeMaxAltFilter.toLocaleString()} ft`;
  }
  if (current3DPoints) {
    renderThreeCubes(current3DPoints);
  }
}

function stepThreeMaxAlt(deltaFt) {
  const slider = document.getElementById("threeMaxAltSlider");
  if (!slider) return;
  const current = parseInt(slider.value, 10);
  const min = parseInt(slider.min, 10);
  const max = parseInt(slider.max, 10);
  const next = Math.max(min, Math.min(max, current + deltaFt));
  slider.value = next;
  onThreeMaxAltChange(next);
}

function renderThreeCubes(points) {
  if (!threeCubeGroup || !points) return;
  current3DPoints = points;

  // Extract altitude bounds and update slider range
  if (points.length > 0) {
    const alts = [...new Set(points.map(p => p.alt_ft))].sort((a, b) => a - b);
    const minAlt = alts[0];
    const maxAlt = alts[alts.length - 1];

    const slider = document.getElementById("threeMaxAltSlider");
    const label = document.getElementById("threeMaxAltLabel");
    if (slider) {
      slider.min = minAlt;
      slider.max = maxAlt;
      slider.step = 1000;
      if (threeMaxAltFilter === Infinity || threeMaxAltFilter > maxAlt || threeMaxAltFilter < minAlt) {
        threeMaxAltFilter = maxAlt;
        slider.value = maxAlt;
      }
      if (label) {
        label.textContent = `${threeMaxAltFilter.toLocaleString()} ft`;
      }
    }
  }

  // Clear previous cubes
  while (threeCubeGroup.children.length > 0) {
    const obj = threeCubeGroup.children[0];
    threeCubeGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) obj.material.dispose();
  }

  const geom = new THREE.BoxGeometry(2.0, 2.0, 0.6);
  const matLos = new THREE.MeshLambertMaterial({ color: 0x22c55e, opacity: 0.75, transparent: true });
  const matBlocked = new THREE.MeshLambertMaterial({ color: 0xef4444, opacity: 0.35, transparent: true });

  const showBlocked = document.getElementById("threeShowBlocked") ? document.getElementById("threeShowBlocked").checked : false;

  // Filter points up to selected max altitude ceiling
  const visiblePoints = points.filter(p => p.alt_ft <= threeMaxAltFilter);

  // Update visible cube counter
  const countLabel = document.getElementById("threeCubeCountLabel");
  if (countLabel) {
    const hiddenCount = points.length - visiblePoints.length;
    countLabel.textContent = `Showing ${visiblePoints.length.toLocaleString()} cubes` + (hiddenCount > 0 ? ` (${hiddenCount.toLocaleString()} hidden above)` : ` (all altitudes)`);
  }

  // Use InstancedMesh for high performance
  const count = visiblePoints.length;
  if (count === 0) return;

  const instLos = new THREE.InstancedMesh(geom, matLos, count);
  const instBlocked = new THREE.InstancedMesh(geom, matBlocked, count);

  const dummy = new THREE.Object3D();
  let losIdx = 0;
  let blockedIdx = 0;

  visiblePoints.forEach(p => {
    dummy.position.set(p.x, p.y, p.z);
    dummy.updateMatrix();

    if (p.is_los) {
      instLos.setMatrixAt(losIdx++, dummy.matrix);
    } else if (showBlocked) {
      instBlocked.setMatrixAt(blockedIdx++, dummy.matrix);
    }
  });

  instLos.count = losIdx;
  instLos.instanceMatrix.needsUpdate = true;
  threeCubeGroup.add(instLos);

  if (showBlocked && blockedIdx > 0) {
    instBlocked.count = blockedIdx;
    instBlocked.instanceMatrix.needsUpdate = true;
    threeCubeGroup.add(instBlocked);
  }

  threeCubeGroup.scale.set(1.0, 1.0, threeZScale);
}

function toggleThreeBlockedCubes(show) {
  if (current3DPoints) {
    renderThreeCubes(current3DPoints);
  }
}

const DEFAULT_TECH_PROFILES = {
  SSR_RADAR: {
    id: "SSR_RADAR",
    name: "SSR Radar / Mode S & ADS-B (1030 / 1090 MHz)",
    category: "Aviation Surveillance & IFF",
    standard: "ICAO Annex 10 Vol IV / EUROCAE ED-102B",
    description: "Secondary Surveillance Radar interrogator (1030 MHz) and transponder / ADS-B reply (1090 MHz)",
    frequencies: [
      {
        id: "ssr_uplink",
        label: "Interrogation Uplink (1030 MHz)",
        direction: "Ground Interrogator → Aircraft",
        freq_hz: 1030.0e6,
        tx_power_dbm: 61.8,
        tx_gain_dbi: 27.0,
        rx_gain_dbi: 3.0,
        rx_sensitivity_dbm: -74.0,
        fade_margin_db: 6.0,
        channel_bw_mhz: 2.0
      },
      {
        id: "ssr_downlink",
        label: "Reply Downlink / ADS-B (1090 MHz)",
        direction: "Aircraft Transponder → Ground Station",
        freq_hz: 1090.0e6,
        tx_power_dbm: 54.0,
        tx_gain_dbi: 3.0,
        rx_gain_dbi: 27.0,
        rx_sensitivity_dbm: -90.0,
        fade_margin_db: 6.0,
        channel_bw_mhz: 2.0
      }
    ]
  },
  AIRBAND_VHF: {
    id: "AIRBAND_VHF",
    name: "Aviation VHF Airband AM (Voice & Data)",
    category: "Aeronautical Communications",
    standard: "ICAO Annex 10 Vol III / 8.33 kHz & 25 kHz",
    description: "Civil aviation AM voice communication and VDL Mode 2 air-ground CPDLC data link",
    frequencies: [
      {
        id: "airband_voice_enroute",
        label: "ATC En-Route Voice (125.0 MHz)",
        direction: "Ground Station ↔ Aircraft (Duplex Voice)",
        freq_hz: 125.0e6,
        tx_power_dbm: 44.0,
        tx_gain_dbi: 6.0,
        rx_gain_dbi: 2.0,
        rx_sensitivity_dbm: -107.0,
        fade_margin_db: 10.0,
        channel_bw_mhz: 0.025
      },
      {
        id: "airband_guard",
        label: "Emergency Guard Channel (121.5 MHz)",
        direction: "Distress & Guard Broadcast",
        freq_hz: 121.5e6,
        tx_power_dbm: 44.0,
        tx_gain_dbi: 6.0,
        rx_gain_dbi: 2.0,
        rx_sensitivity_dbm: -107.0,
        fade_margin_db: 10.0,
        channel_bw_mhz: 0.025
      },
      {
        id: "airband_vdl2",
        label: "VDL Mode 2 CPDLC Data (136.975 MHz)",
        direction: "Air-Ground Packet Data",
        freq_hz: 136.975e6,
        tx_power_dbm: 43.0,
        tx_gain_dbi: 6.0,
        rx_gain_dbi: 2.0,
        rx_sensitivity_dbm: -104.0,
        fade_margin_db: 8.0,
        channel_bw_mhz: 0.025
      }
    ]
  },
  LDACS: {
    id: "LDACS",
    name: "LDACS (L-band Digital Aeronautical Communications)",
    category: "Future ATM Broadband Data Link",
    standard: "ICAO Doc 9871 / SESAR PJ14 / Eurocae ED-262",
    description: "L-band cellular-like broadband air-ground data link for trajectory-based operations (TBO)",
    frequencies: [
      {
        id: "ldacs_fl",
        label: "Forward Link FL (Ground → Air, 985.5 MHz)",
        direction: "Ground Station → Aircraft (OFDMA Broadcast)",
        freq_hz: 985.5e6,
        tx_power_dbm: 46.0,
        tx_gain_dbi: 10.0,
        rx_gain_dbi: 3.0,
        rx_sensitivity_dbm: -102.0,
        fade_margin_db: 8.0,
        channel_bw_mhz: 0.5
      },
      {
        id: "ldacs_rl",
        label: "Reverse Link RL (Air → Ground, 1025.5 MHz)",
        direction: "Aircraft → Ground Station (OFDMA Access)",
        freq_hz: 1025.5e6,
        tx_power_dbm: 43.0,
        tx_gain_dbi: 3.0,
        rx_gain_dbi: 10.0,
        rx_sensitivity_dbm: -105.0,
        fade_margin_db: 8.0,
        channel_bw_mhz: 0.5
      }
    ]
  },
  CELLULAR_5G: {
    id: "CELLULAR_5G",
    name: "5G NR Cellular (Sub-6 GHz FR1 - Bands n78 & n28)",
    category: "Mobile Broadband Network",
    standard: "3GPP Release 16/17 NR FR1",
    description: "Commercial 5G New Radio macro site delivering high-throughput mid-band and extended low-band coverage",
    frequencies: [
      {
        id: "5g_n78_midband",
        label: "Band n78 Mid-Band C-Band (3500 MHz)",
        direction: "gNodeB Base Station → UE User Equipment",
        freq_hz: 3500.0e6,
        tx_power_dbm: 53.0,
        tx_gain_dbi: 24.0,
        rx_gain_dbi: 0.0,
        rx_sensitivity_dbm: -98.0,
        fade_margin_db: 12.0,
        channel_bw_mhz: 100.0
      },
      {
        id: "5g_n28_lowband",
        label: "Band n28 Low-Band (700 MHz)",
        direction: "gNodeB Base Station → UE User Equipment",
        freq_hz: 700.0e6,
        tx_power_dbm: 49.0,
        tx_gain_dbi: 18.0,
        rx_gain_dbi: 0.0,
        rx_sensitivity_dbm: -101.0,
        fade_margin_db: 10.0,
        channel_bw_mhz: 20.0
      }
    ]
  },
  TETRA_PMR: {
    id: "TETRA_PMR",
    name: "PMR / TETRA Public Safety (380 / 390 MHz)",
    category: "Mission Critical PMR/LMR",
    standard: "ETSI EN 300 392",
    description: "TETRA digital trunked radio network for emergency services, police, and airport ramp ops",
    frequencies: [
      {
        id: "tetra_downlink",
        label: "Base Station Downlink (390.0 MHz)",
        direction: "Base Station → Handheld Radio",
        freq_hz: 390.0e6,
        tx_power_dbm: 44.0,
        tx_gain_dbi: 8.0,
        rx_gain_dbi: 0.0,
        rx_sensitivity_dbm: -115.0,
        fade_margin_db: 10.0,
        channel_bw_mhz: 0.025
      },
      {
        id: "tetra_uplink",
        label: "Handheld Radio Uplink (380.0 MHz)",
        direction: "Handheld Radio → Base Station",
        freq_hz: 380.0e6,
        tx_power_dbm: 37.0,
        tx_gain_dbi: 0.0,
        rx_gain_dbi: 8.0,
        rx_sensitivity_dbm: -118.0,
        fade_margin_db: 10.0,
        channel_bw_mhz: 0.025
      }
    ]
  },
  MICROWAVE_BACKHAUL: {
    id: "MICROWAVE_BACKHAUL",
    name: "Point-to-Point Microwave Backhaul (13 GHz FDD)",
    category: "Fixed Wireless Transport",
    standard: "ETSI EN 302 217 / ITU-R F.746",
    description: "High-capacity line-of-sight microwave trunk link connecting remote radar/comm sites",
    frequencies: [
      {
        id: "mw_subband_low",
        label: "Low Sub-Band FDD (12.75 GHz)",
        direction: "Site A → Site B (1024-QAM Trunk)",
        freq_hz: 12750.0e6,
        tx_power_dbm: 30.0,
        tx_gain_dbi: 38.0,
        rx_gain_dbi: 38.0,
        rx_sensitivity_dbm: -78.0,
        fade_margin_db: 15.0,
        channel_bw_mhz: 56.0
      },
      {
        id: "mw_subband_high",
        label: "High Sub-Band FDD (13.25 GHz)",
        direction: "Site B → Site A (1024-QAM Trunk)",
        freq_hz: 13250.0e6,
        tx_power_dbm: 30.0,
        tx_gain_dbi: 38.0,
        rx_gain_dbi: 38.0,
        rx_sensitivity_dbm: -78.0,
        fade_margin_db: 15.0,
        channel_bw_mhz: 56.0
      }
    ]
  }
};

let currentTechProfiles = DEFAULT_TECH_PROFILES;
let activeTechProfileKey = "SSR_RADAR";
let activeChannelIdx = 1; // Default to 1090 MHz (Reply Downlink / ADS-B)
let channelParamOverrides = {};

/* =========================================================================
   3. API INTEGRATION & CALCULATIONS
   ========================================================================= */
async function loadPresets() {
  try {
    const res = await fetch("/api/presets");
    currentPresets = await res.json();

    // Populate Location Presets
    const locSelect = document.getElementById("locationPreset");
    if (locSelect && currentPresets.sample_locations) {
      locSelect.innerHTML = '<option value="">-- Custom Coordinates --</option>';
      currentPresets.sample_locations.forEach((loc, idx) => {
        const opt = document.createElement("option");
        opt.value = idx;
        opt.textContent = `${loc.name} (${Math.round(loc.alt_amsl_m)} m)`;
        locSelect.appendChild(opt);
      });
    }

    // Populate Technology & System Profiles in top header, sidebar, and budget tab
    if (currentPresets.technology_profiles && Object.keys(currentPresets.technology_profiles).length > 0) {
      currentTechProfiles = currentPresets.technology_profiles;
    } else {
      currentTechProfiles = DEFAULT_TECH_PROFILES;
    }
    populateTechnologySelectors();

  } catch (err) {
    console.error("Failed to load presets, using default technology profiles:", err);
    currentTechProfiles = DEFAULT_TECH_PROFILES;
    populateTechnologySelectors();
  }
}

function populateTechnologySelectors() {
  const topSel = document.getElementById("techSystemSelect");
  const sideSel = document.getElementById("techSelectSidebar");
  const tbSel = document.getElementById("tbTechSelect");

  const buildOptions = (targetSel) => {
    if (!targetSel) return;
    targetSel.innerHTML = '<option value="custom">-- Custom Frequency / Transceiver --</option>';
    for (const [key, prof] of Object.entries(currentTechProfiles)) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = prof.name;
      if (key === activeTechProfileKey) opt.selected = true;
      targetSel.appendChild(opt);
    }
    targetSel.value = activeTechProfileKey;
  };

  buildOptions(topSel);
  buildOptions(sideSel);
  buildOptions(tbSel);

  applyTechnologyProfile(activeTechProfileKey);
}

function onTechnologySystemChange() {
  const sel = document.getElementById("techSystemSelect");
  if (!sel) return;
  const key = sel.value;
  activeTechProfileKey = key;
  const sideSel = document.getElementById("techSelectSidebar");
  if (sideSel) sideSel.value = key;
  const tbSel = document.getElementById("tbTechSelect");
  if (tbSel) tbSel.value = key;
  applyTechnologyProfile(key);
}

function onSidebarTechSelectChange() {
  const sel = document.getElementById("techSelectSidebar");
  if (!sel) return;
  const key = sel.value;
  activeTechProfileKey = key;
  const topSel = document.getElementById("techSystemSelect");
  if (topSel) topSel.value = key;
  const tbSel = document.getElementById("tbTechSelect");
  if (tbSel) tbSel.value = key;
  applyTechnologyProfile(key);
}

function onTbTechSelectChange() {
  const sel = document.getElementById("tbTechSelect");
  if (!sel) return;
  const key = sel.value;
  activeTechProfileKey = key;
  const topSel = document.getElementById("techSystemSelect");
  if (topSel) topSel.value = key;
  const sideSel = document.getElementById("techSelectSidebar");
  if (sideSel) sideSel.value = key;
  applyTechnologyProfile(key);
}

function applyTechnologyProfile(key) {
  if (key === "custom" || !currentTechProfiles[key]) {
    document.getElementById("techChannelPillsContainer").style.display = "none";
    updateSidebarLinkBudgetMetrics();
    renderTechnologyBudgetTab();
    return;
  }

  document.getElementById("techChannelPillsContainer").style.display = "block";
  const prof = currentTechProfiles[key];

  // Render channel pills in sidebar
  const pillsBox = document.getElementById("techChannelPills");
  pillsBox.innerHTML = "";

  prof.frequencies.forEach((chan, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `pill-channel-btn ${idx === activeChannelIdx ? 'active' : ''}`;
    btn.innerHTML = `
      <span><b>${chan.freq_hz / 1e6} MHz</b> &middot; ${chan.label.split('(')[0].trim()}</span>
      <span style="font-size:10px; opacity:0.8;">${chan.direction.includes('→') ? chan.direction.split('→')[0].trim() : ''}</span>
    `;
    btn.onclick = () => selectTechnologyChannel(idx);
    pillsBox.appendChild(btn);
  });

  // Clamp active channel index
  if (activeChannelIdx >= prof.frequencies.length) {
    activeChannelIdx = 0;
  }

  const activeChan = prof.frequencies[activeChannelIdx];
  if (activeChan) {
    document.getElementById("freqMhz").value = activeChan.freq_hz / 1e6;
    onFreqChange();
    const chan = getActiveChannelParams(activeChan.id, activeChan);
    syncLinkBudgetTabInputs(chan);
  }

  updateSidebarLinkBudgetMetrics();
  renderTechnologyBudgetTab();
  calculateCoverage();
}

function selectTechnologyChannel(idx) {
  activeChannelIdx = idx;
  const prof = currentTechProfiles[activeTechProfileKey];
  if (!prof || !prof.frequencies[idx]) return;

  const chan = prof.frequencies[idx];
  document.getElementById("freqMhz").value = chan.freq_hz / 1e6;
  onFreqChange();
  const activeChan = getActiveChannelParams(chan.id, chan);
  syncLinkBudgetTabInputs(activeChan);

  // Update pills active state
  const btns = document.querySelectorAll("#techChannelPills .pill-channel-btn");
  btns.forEach((b, i) => {
    if (i === idx) b.classList.add("active");
    else b.classList.remove("active");
  });

  updateSidebarLinkBudgetMetrics();
  renderTechnologyBudgetTab();
  calculateCoverage();
}

function syncLinkBudgetTabInputs(chan) {
  if (!chan) return;
  const txP = document.getElementById("linkTxPowerDbm");
  if (txP) txP.value = chan.tx_power_dbm;
  const txG = document.getElementById("linkTxGainDbi");
  if (txG) txG.value = chan.tx_gain_dbi;
  const rxG = document.getElementById("linkRxGainDbi");
  if (rxG) rxG.value = chan.rx_gain_dbi;
  const rxS = document.getElementById("linkRxSensDbm");
  if (rxS) rxS.value = chan.rx_sensitivity_dbm;
  const fade = document.getElementById("linkFadeMarginDb");
  if (fade) fade.value = chan.fade_margin_db;

  const watts = Math.pow(10, (chan.tx_power_dbm - 30.0) / 10.0);
  let wattsStr = "";
  if (watts >= 1000.0) wattsStr = `= ${(watts / 1000.0).toFixed(1)} kW`;
  else if (watts >= 1.0) wattsStr = `= ${watts.toFixed(1)} W`;
  else if (watts >= 0.001) wattsStr = `= ${(watts * 1000.0).toFixed(1)} mW`;
  else wattsStr = `= ${(watts * 1e6).toFixed(1)} µW`;
  const wEl = document.getElementById("linkTxWattsLabel");
  if (wEl) wEl.textContent = wattsStr;

  const mapl = chan.tx_power_dbm + chan.tx_gain_dbi + chan.rx_gain_dbi - chan.rx_sensitivity_dbm - chan.fade_margin_db;
  const statEl = document.getElementById("statMaplValue");
  if (statEl) statEl.textContent = `${mapl.toFixed(1)} dB`;
}

function getActiveChannelParams(chanId, defaultChan) {
  if (channelParamOverrides[chanId]) {
    return { ...defaultChan, ...channelParamOverrides[chanId] };
  }
  return { ...defaultChan };
}

function updateSidebarLinkBudgetMetrics() {
  let txP, txG, rxG, rxS, fade;

  const prof = currentTechProfiles ? currentTechProfiles[activeTechProfileKey] : null;
  if (prof && prof.frequencies && prof.frequencies[activeChannelIdx]) {
    const defaultChan = prof.frequencies[activeChannelIdx];
    const chan = getActiveChannelParams(defaultChan.id, defaultChan);
    txP = parseFloat(chan.tx_power_dbm) || 0;
    txG = parseFloat(chan.tx_gain_dbi) || 0;
    rxG = parseFloat(chan.rx_gain_dbi) || 0;
    rxS = parseFloat(chan.rx_sensitivity_dbm) || -90;
    fade = parseFloat(chan.fade_margin_db) || 0;
  } else {
    // Custom transceiver profile from link budget tab
    txP = parseFloat(document.getElementById("linkTxPowerDbm")?.value) || 54.0;
    txG = parseFloat(document.getElementById("linkTxGainDbi")?.value) || 12.0;
    rxG = parseFloat(document.getElementById("linkRxGainDbi")?.value) || 3.0;
    rxS = parseFloat(document.getElementById("linkRxSensDbm")?.value) || -90.0;
    fade = parseFloat(document.getElementById("linkFadeMarginDb")?.value) || 10.0;
  }

  const mapl = txP + txG + rxG - rxS - fade;

  const maplEl = document.getElementById("sidebarMaplVal");
  if (maplEl) maplEl.textContent = `${mapl.toFixed(1)} dB`;

  const txPEl = document.getElementById("sidebarTxPowerVal");
  if (txPEl) txPEl.textContent = `${txP >= 0 ? '+' : ''}${txP.toFixed(1)} dBm`;

  const txGEl = document.getElementById("sidebarTxGainVal");
  if (txGEl) txGEl.textContent = `${txG >= 0 ? '+' : ''}${txG.toFixed(1)} dBi`;

  const rxSEl = document.getElementById("sidebarRxSensVal");
  if (rxSEl) rxSEl.textContent = `${rxS >= 0 ? '+' : ''}${rxS.toFixed(1)} dBm`;

  const rxGEl = document.getElementById("sidebarRxGainVal");
  if (rxGEl) rxGEl.textContent = `${rxG >= 0 ? '+' : ''}${rxG.toFixed(1)} dBi`;

  const fadeEl = document.getElementById("sidebarFadeVal");
  if (fadeEl) fadeEl.textContent = `${fade.toFixed(1)} dB`;

  const legacyTxRxEl = document.getElementById("sidebarTxRxVal");
  if (legacyTxRxEl) {
    legacyTxRxEl.textContent = `${txP.toFixed(1)} dBm / ${rxS.toFixed(1)} dBm`;
  }

  const calcEl = document.getElementById("sidebarMaplCalcLine");
  if (calcEl) {
    const rxSensStr = rxS < 0 ? `(&minus;${Math.abs(rxS).toFixed(1)})` : rxS.toFixed(1);
    calcEl.innerHTML = `${txP.toFixed(1)} + ${txG.toFixed(1)} + ${rxG.toFixed(1)} &minus; ${rxSensStr} &minus; ${fade.toFixed(1)} = <b style="color:var(--accent-cyan);">${mapl.toFixed(1)} dB</b>`;
  }
}

function onChannelParamChange(chanId, paramName, value) {
  if (!channelParamOverrides[chanId]) {
    channelParamOverrides[chanId] = {};
  }
  channelParamOverrides[chanId][paramName] = parseFloat(value);
  updateSidebarLinkBudgetMetrics();
  renderTechnologyBudgetTab();
}

function resetChannelParams(chanId) {
  if (channelParamOverrides[chanId]) {
    delete channelParamOverrides[chanId];
  }
  updateSidebarLinkBudgetMetrics();
  renderTechnologyBudgetTab();
}

function calcKnifeEdgeLoss(v) {
  if (v <= -0.7) return 0.0;
  return 6.9 + 20.0 * Math.log10(Math.sqrt(Math.pow(v - 0.1, 2) + 1.0) + (v - 0.1));
}

function renderTechnologyBudgetTab() {
  const container = document.getElementById("tbChannelCardsContainer");
  if (!container) return;

  const rangeKm = parseFloat(document.getElementById("rangeKm")?.value) || 100;
  const bearing = parseFloat(document.getElementById("radialBearing")?.value) || 45;
  const altFt = parseFloat(document.getElementById("altSliceFt")?.value) || 10000;

  // Update target ray pill
  const targetRangeEl = document.getElementById("tbTargetRange");
  if (targetRangeEl) targetRangeEl.textContent = `${rangeKm} km`;
  const targetBearingEl = document.getElementById("tbTargetBearing");
  if (targetBearingEl) targetBearingEl.textContent = `${bearing.toString().padStart(3, "0")}°`;
  const targetAltEl = document.getElementById("tbTargetAlt");
  if (targetAltEl) targetAltEl.textContent = `${parseInt(altFt, 10).toLocaleString()} ft`;

  const isCustom = activeTechProfileKey === "custom" || !currentTechProfiles || !currentTechProfiles[activeTechProfileKey];

  let prof = null;
  let channels = [];

  if (isCustom) {
    const fMhz = parseFloat(document.getElementById("freqMhz")?.value) || 1000;
    const txP = parseFloat(document.getElementById("linkTxPowerDbm")?.value) || 54.0;
    const txG = parseFloat(document.getElementById("linkTxGainDbi")?.value) || 12.0;
    const rxG = parseFloat(document.getElementById("linkRxGainDbi")?.value) || 3.0;
    const rxS = parseFloat(document.getElementById("linkRxSensDbm")?.value) || -90.0;
    const fade = parseFloat(document.getElementById("linkFadeMarginDb")?.value) || 10.0;

    prof = {
      name: "Custom Transceiver Profile",
      category: "User-Defined RF Configuration",
      standard: "Arbitrary Frequency & Transceiver Parameters",
      description: "Custom user-specified transmitter, antenna and receiver sensitivities evaluated along the current target ray."
    };

    channels = [{
      id: "custom_chan",
      label: `Custom Channel (${fMhz} MHz)`,
      direction: "Transmitter → Target Receiver",
      freq_hz: fMhz * 1e6,
      tx_power_dbm: txP,
      tx_gain_dbi: txG,
      rx_gain_dbi: rxG,
      rx_sensitivity_dbm: rxS,
      fade_margin_db: fade,
      channel_bw_mhz: 1.0
    }];
  } else {
    prof = currentTechProfiles[activeTechProfileKey];
    channels = prof.frequencies;
  }

  // Update system metadata card
  const titleEl = document.getElementById("tbSystemTitle");
  if (titleEl) titleEl.textContent = prof.name;
  const catEl = document.getElementById("tbSystemCategory");
  if (catEl) catEl.textContent = prof.category || "RF System";
  const stdEl = document.getElementById("tbSystemStandard");
  if (stdEl) stdEl.textContent = `Standard: ${prof.standard || "N/A"}`;
  const descEl = document.getElementById("tbSystemDesc");
  if (descEl) descEl.textContent = prof.description || "";

  // Reference frequency and diffraction parameter from activeRadialData
  let refFreqHz = (parseFloat(document.getElementById("freqMhz")?.value) || 1000) * 1e6;
  let refDiffV = 0.0;
  let refHasObstacle = false;

  if (activeRadialData && activeRadialData.frequencies) {
    const fKeys = Object.keys(activeRadialData.frequencies);
    if (fKeys.length > 0) {
      const fData = activeRadialData.frequencies[fKeys[0]];
      refFreqHz = parseFloat(fKeys[0]);
      refDiffV = fData.diffraction_v || 0.0;
      refHasObstacle = !activeRadialData.radio_los;
    }
  }

  container.innerHTML = "";
  const channelResults = [];

  channels.forEach((defaultChan, idx) => {
    const chan = getActiveChannelParams(defaultChan.id, defaultChan);
    const fMhz = chan.freq_hz / 1e6;
    const lamM = 299792458 / chan.freq_hz;
    const lamStr = lamM >= 1.0 ? `${lamM.toFixed(2)} m` : `${(lamM * 100).toFixed(1)} cm`;

    // 1. MAPL: Tx_P + Tx_G + Rx_G - Rx_S - Fade_Margin
    const mapl = chan.tx_power_dbm + chan.tx_gain_dbi + chan.rx_gain_dbi - chan.rx_sensitivity_dbm - chan.fade_margin_db;

    // 2. FSPL: 20 log10(d_km) + 20 log10(f_mhz) + 32.44
    const fspl = 20.0 * Math.log10(Math.max(0.1, rangeKm)) + 20.0 * Math.log10(fMhz) + 32.44;

    // 3. Knife-Edge Diffraction
    let diffLoss = 0.0;
    if (refHasObstacle && refDiffV > -0.7) {
      const vChan = refDiffV * Math.sqrt(chan.freq_hz / refFreqHz);
      diffLoss = calcKnifeEdgeLoss(vChan);
    }
    const totalLoss = fspl + diffLoss;

    // 4. Link Margin
    const margin = mapl - totalLoss;
    const linkClosed = margin >= 0.0;

    // 5. Max Operational Range (Free Space)
    const rMax = Math.pow(10, (mapl - 32.44 - 20.0 * Math.log10(fMhz)) / 20.0);

    // Watts conversion
    const pWatts = Math.pow(10, (chan.tx_power_dbm - 30.0) / 10.0);
    let pWattsStr = "";
    if (pWatts >= 1000.0) pWattsStr = `${(pWatts / 1000.0).toFixed(1)} kW`;
    else if (pWatts >= 1.0) pWattsStr = `${pWatts.toFixed(1)} W`;
    else if (pWatts >= 0.001) pWattsStr = `${(pWatts * 1000.0).toFixed(1)} mW`;
    else pWattsStr = `${(pWatts * 1e6).toFixed(1)} µW`;

    // Margin meter percentage [-20 dB, +40 dB] -> [0%, 100%]
    const meterPct = Math.min(100, Math.max(0, ((margin + 20.0) / 60.0) * 100.0));
    let meterColor = "#22c55e";
    if (margin < 0) meterColor = "#ef4444";
    else if (margin < 6) meterColor = "#f59e0b";

    const isSelectedActive = (!isCustom && idx === activeChannelIdx) || (isCustom && idx === 0);

    channelResults.push({
      ...chan,
      fMhz,
      mapl,
      fspl,
      diffLoss,
      totalLoss,
      margin,
      linkClosed,
      rMax
    });

    const card = document.createElement("div");
    card.className = "channel-card";
    if (isSelectedActive) {
      card.style.borderColor = "var(--accent-cyan)";
      card.style.boxShadow = "0 0 16px rgba(56, 189, 248, 0.25)";
    }

    card.innerHTML = `
      <div class="channel-card-header">
        <div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="channel-card-title">${chan.label}</span>
            ${isSelectedActive ? '<span style="font-size:10px; font-weight:700; background:rgba(56, 189, 248, 0.2); color:var(--accent-cyan); border:1px solid rgba(56, 189, 248, 0.4); padding:2px 6px; border-radius:4px;">ACTIVE RAY</span>' : ''}
          </div>
          <div class="channel-card-direction">${chan.direction} &middot; &lambda; = ${lamStr}</div>
        </div>
        <div>
          ${!isSelectedActive && !isCustom ? `<button class="btn btn-secondary" style="font-size:10.5px; padding:3px 8px;" onclick="selectTechnologyChannel(${idx})">Select for Ray</button>` : ''}
        </div>
      </div>

      <!-- Editable Link Budget Parameters Grid -->
      <div class="channel-grid-params">
        <div class="param-item">
          <label>Tx Power (dBm)</label>
          <input type="number" step="0.5" value="${chan.tx_power_dbm.toFixed(1)}" onchange="onChannelParamChange('${chan.id}', 'tx_power_dbm', this.value)" />
          <div style="font-size:9.5px; color:var(--accent-blue); margin-top:2px;">= ${pWattsStr}</div>
        </div>
        <div class="param-item">
          <label>Tx Gain (dBi)</label>
          <input type="number" step="0.5" value="${chan.tx_gain_dbi.toFixed(1)}" onchange="onChannelParamChange('${chan.id}', 'tx_gain_dbi', this.value)" />
        </div>
        <div class="param-item">
          <label>Rx Gain (dBi)</label>
          <input type="number" step="0.5" value="${chan.rx_gain_dbi.toFixed(1)}" onchange="onChannelParamChange('${chan.id}', 'rx_gain_dbi', this.value)" />
        </div>
        <div class="param-item">
          <label>Rx Sens (dBm)</label>
          <input type="number" step="0.5" value="${chan.rx_sensitivity_dbm.toFixed(1)}" onchange="onChannelParamChange('${chan.id}', 'rx_sensitivity_dbm', this.value)" />
        </div>
        <div class="param-item">
          <label>Fade Margin (dB)</label>
          <input type="number" step="0.5" value="${chan.fade_margin_db.toFixed(1)}" onchange="onChannelParamChange('${chan.id}', 'fade_margin_db', this.value)" />
        </div>
        <div class="param-item" style="display:flex; flex-direction:column; justify-content:center; align-items:flex-end;">
          <button type="button" class="btn btn-secondary" style="font-size:9.5px; padding:2px 6px; color:var(--text-muted);" onclick="resetChannelParams('${chan.id}')" title="Reset to standard defaults">↺ Reset</button>
        </div>
      </div>

      <!-- Link Assessment Metrics Breakdown -->
      <div style="background:rgba(15, 23, 42, 0.4); border-radius:6px; padding:10px; font-size:11.5px; display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; border:1px solid rgba(255, 255, 255, 0.04);">
        <div>
          <span style="color:var(--text-muted); font-size:10px; display:block;">MAPL (Limit)</span>
          <span style="font-weight:700; color:#fff; font-size:13px;">${mapl.toFixed(1)} dB</span>
        </div>
        <div>
          <span style="color:var(--text-muted); font-size:10px; display:block;">FSPL (Free Space)</span>
          <span style="font-weight:600; color:var(--accent-cyan);">${fspl.toFixed(1)} dB</span>
        </div>
        <div>
          <span style="color:var(--text-muted); font-size:10px; display:block;">Diffraction Loss</span>
          <span style="font-weight:600; color:${diffLoss > 0 ? '#ef4444' : 'var(--accent-green)'};">${diffLoss.toFixed(1)} dB</span>
        </div>
        <div>
          <span style="color:var(--text-muted); font-size:10px; display:block;">Total Path Loss</span>
          <span style="font-weight:700; color:#fff; font-size:13px;">${totalLoss.toFixed(1)} dB</span>
        </div>
      </div>

      <!-- Link Closure Banner -->
      <div class="link-result-banner ${linkClosed ? 'closed' : 'dropped'}">
        <div>
          <div style="font-size:10px; text-transform:uppercase; font-weight:700; color:${linkClosed ? 'var(--accent-green)' : 'var(--accent-red)'}; letter-spacing:0.5px;">
            ${linkClosed ? '✔ LINK BUDGET CLOSED' : '✖ LINK BUDGET DROPPED'}
          </div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">
            Max Line-of-Sight Range (Free Space): <b style="color:#fff;">${rMax >= 1000 ? rMax.toFixed(0) : rMax.toFixed(1)} km</b>
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:16px; font-weight:800; color:${linkClosed ? 'var(--accent-green)' : 'var(--accent-red)'};">
            ${margin >= 0 ? `+${margin.toFixed(1)}` : margin.toFixed(1)} dB
          </div>
          <div style="font-size:10px; color:var(--text-muted);">Link Margin</div>
        </div>
      </div>

      <!-- Margin Meter -->
      <div style="margin-top:-6px;">
        <div style="display:flex; justify-content:space-between; font-size:9.5px; color:var(--text-muted); margin-bottom:2px;">
          <span>-20 dB (Critical Outage)</span>
          <span>0 dB (Threshold)</span>
          <span>+40 dB (Robust)</span>
        </div>
        <div class="link-margin-meter">
          <div class="link-margin-meter-fill" style="width:${meterPct}%; background:${meterColor};"></div>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  // Render Link Balance & Bottleneck Summary
  renderSystemBalanceSummary(prof, channelResults);
}

function renderSystemBalanceSummary(prof, channels) {
  const box = document.getElementById("tbBalanceSummary");
  if (!box) return;

  if (channels.length < 2) {
    box.innerHTML = `
      <div style="color:var(--text-muted);">
        Single channel active. Link margin is <b>${channels[0].margin >= 0 ? '+' : ''}${channels[0].margin.toFixed(1)} dB</b> at the current target distance of <b>${document.getElementById("rangeKm")?.value || 100} km</b>. 
        Theoretical maximum operational range in free space is <b>${channels[0].rMax.toFixed(1)} km</b>.
      </div>
    `;
    return;
  }

  // Sort by margin to find bottleneck
  const sorted = [...channels].sort((a, b) => a.margin - b.margin);
  const bottleneck = sorted[0];
  const strong = sorted[sorted.length - 1];
  const marginDelta = Math.abs(strong.margin - bottleneck.margin);
  const maplDelta = Math.abs(strong.mapl - bottleneck.mapl);

  let techInsight = "";
  if (activeTechProfileKey === "SSR_RADAR") {
    techInsight = `
      <b>Secondary Surveillance Radar Asymmetry:</b> Mode S / ADS-B interrogation and replies are inherently asymmetric. 
      The ground station utilizes a powerful 1.5 kW transmitter into a high-gain rotating array (27 dBi), but the transponder has a high trigger threshold (-74 dBm). 
      Conversely, the aircraft transponder emits 250 W via an omnidirectional blade antenna (3 dBi), relying on high ground receiver sensitivity (-90 dBm). 
      Here, <b>${bottleneck.label}</b> is the limiting link direction with a margin difference of <b>${marginDelta.toFixed(1)} dB</b>.
    `;
  } else if (activeTechProfileKey === "AIRBAND_VHF") {
    techInsight = `
      <b>VHF Airband Voice Dynamics:</b> Civil aviation AM voice operates with 25 W ground transmitters and 16–25 W airborne transceivers. 
      Because free-space loss at 118–137 MHz is relatively low (~114 dB at 100 km) and receiver sensitivity is high (-107 dBm for readable 12 dB SINAD audio), 
      the air-ground link maintains a large positive fade margin. Clearance is primarily dictated by the radio horizon and terrain diffraction rather than thermal noise.
    `;
  } else if (activeTechProfileKey === "LDACS") {
    techInsight = `
      <b>LDACS Cellular Air-Ground Balance:</b> The Forward Link (985.5 MHz) benefits from a 40 W ground sector transmitter with 10 dBi gain. 
      The Reverse Link (1025.5 MHz) is power-constrained by the aircraft's 20 W transmitter and 3 dBi antenna. 
      The <b>${bottleneck.label}</b> is the bottleneck with a <b>${marginDelta.toFixed(1)} dB</b> deficit relative to the forward broadcast, requiring robust QPSK coding near the cell boundary.
    `;
  } else if (activeTechProfileKey === "CELLULAR_5G") {
    techInsight = `
      <b>5G NR Frequency & Power Balance:</b> Low-band n28 (700 MHz) provides broad coverage with lower path loss, while mid-band n78 (3.5 GHz) offers high bandwidth but suffers from ~14 dB higher free-space path loss and severe diffraction attenuation. 
      The user equipment uplink power (200 mW / 23 dBm) is the fundamental coverage limiter against the 200 W Massive MIMO macro site.
    `;
  } else {
    techInsight = `
      The link assessment indicates that <b>${bottleneck.label}</b> is the bottleneck link with a margin of <b>${bottleneck.margin >= 0 ? '+' : ''}${bottleneck.margin.toFixed(1)} dB</b> 
      (delta of <b>${marginDelta.toFixed(1)} dB</b> vs ${strong.label}).
    `;
  }

  box.innerHTML = `
    <div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:12px; align-items:center;">
      <div style="background:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.35); border-radius:6px; padding:8px 14px;">
        <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Coverage Limiting Bottleneck:</span>
        <div style="font-weight:700; color:#fff; font-size:13px; margin-top:2px;">
          ${bottleneck.label} (${bottleneck.margin >= 0 ? '+' : ''}${bottleneck.margin.toFixed(1)} dB margin)
        </div>
      </div>
      <div style="background:rgba(56, 189, 248, 0.12); border:1px solid rgba(56, 189, 248, 0.35); border-radius:6px; padding:8px 14px;">
        <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Link Budget Asymmetry (&Delta;):</span>
        <div style="font-weight:700; color:var(--accent-cyan); font-size:13px; margin-top:2px;">
          ${marginDelta.toFixed(1)} dB Margin Delta &middot; ${maplDelta.toFixed(1)} dB MAPL Delta
        </div>
      </div>
      <div style="background:rgba(34, 197, 94, 0.12); border:1px solid rgba(34, 197, 94, 0.35); border-radius:6px; padding:8px 14px;">
        <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">System Operability:</span>
        <div style="font-weight:700; color:${bottleneck.linkClosed ? 'var(--accent-green)' : 'var(--accent-red)'}; font-size:13px; margin-top:2px;">
          ${bottleneck.linkClosed ? '✔ FULL DUPLEX / TWO-WAY CLOSURE' : '✖ ASYMMETRIC ONE-WAY DROPOUT'}
        </div>
      </div>
    </div>
    <div style="line-height:1.5; color:var(--text-main); font-size:12px;">
      ${techInsight}
    </div>
  `;
}

function onLocationPresetChange() {
  const sel = document.getElementById("locationPreset");
  if (!currentPresets || sel.value === "") return;
  const loc = currentPresets.sample_locations[parseInt(sel.value, 10)];
  if (loc) {
    document.getElementById("txLat").value = loc.lat;
    document.getElementById("txLon").value = loc.lon;
    const ft = loc.alt_amsl_ft || Math.round((loc.alt_amsl_m || 2962) * 3.28084);
    document.getElementById("txAltFt").value = ft;
    document.getElementById("txAltM").value = Math.round(loc.alt_amsl_m || ft * 0.3048);
    if (map) map.setView([loc.lat, loc.lon], 9);
    calculateCoverage();
  }
}

function onTxAltFtInput(val) {
  const ft = parseFloat(val) || 0;
  const elM = document.getElementById("txAltM");
  if (elM) elM.value = Math.round(ft * 0.3048);
  calculateCoverage();
}

function onFreqChange() {
  const freqMhz = parseFloat(document.getElementById("freqMhz").value) || 1000;
  const lamM = 299792458 / (freqMhz * 1e6);
  let lamText = "";
  if (lamM >= 1.0) lamText = `${lamM.toFixed(2)} m`;
  else if (lamM >= 0.01) lamText = `${(lamM * 100).toFixed(1)} cm`;
  else lamText = `${(lamM * 1000).toFixed(1)} mm`;
  document.getElementById("wavelengthLabel").value = lamText;
}

function updateRangeLabel(val) {
  document.getElementById("rangeKmVal").textContent = `${val} km`;
  updateMapLayers();
}

function updateKFactorLabel(val) {
  document.getElementById("kFactorVal").textContent = parseFloat(val).toFixed(2);
}

function toggleSweepInputs() {
  const box = document.getElementById("freqSweepBox");
  box.style.display = document.getElementById("enableFreqSweep").checked ? "block" : "none";
}

function getIgnoredObstacleRadiusM() {
  const toggle = document.getElementById("toggleCompoundMask");
  if (toggle && !toggle.checked) return 0.0;
  const slider = document.getElementById("compoundRadiusM");
  return slider ? parseFloat(slider.value) || 50.0 : 50.0;
}

function onCompoundMaskToggle(enabled) {
  const badge = document.getElementById("compoundMaskBadge");
  const container = document.getElementById("compoundMaskSliderContainer");
  const radius = parseFloat(document.getElementById("compoundRadiusM")?.value) || 50;
  if (!enabled) {
    if (badge) {
      badge.textContent = "OFF";
      badge.style.color = "#94a3b8";
      badge.style.background = "rgba(148, 163, 184, 0.15)";
      badge.style.borderColor = "rgba(148, 163, 184, 0.3)";
    }
    if (container) container.style.opacity = "0.4";
  } else {
    if (badge) {
      badge.textContent = `${radius} m`;
      badge.style.color = "var(--accent-cyan)";
      badge.style.background = "rgba(6, 182, 212, 0.15)";
      badge.style.borderColor = "rgba(6, 182, 212, 0.3)";
    }
    if (container) container.style.opacity = "1";
  }
  fetchRadialProfile();
  fetchHorizontalSlice();
}

let _compoundDebounceTimer = null;
function onCompoundRadiusInput(val) {
  const radius = parseInt(val, 10);
  const valEl = document.getElementById("compoundRadiusVal");
  const badge = document.getElementById("compoundMaskBadge");
  if (valEl) valEl.textContent = `${radius} m`;
  const toggle = document.getElementById("toggleCompoundMask");
  if (toggle && toggle.checked && badge) {
    badge.textContent = `${radius} m`;
  }
  clearTimeout(_compoundDebounceTimer);
  _compoundDebounceTimer = setTimeout(() => {
    fetchRadialProfile();
    fetchHorizontalSlice();
  }, 250);
}

let _altSliceDebounceTimer = null;
function onAltSliceInput(val) {
  const altFt = parseInt(val, 10);
  document.getElementById("altSliceVal").textContent = `${altFt.toLocaleString()} ft`;
  document.getElementById("badgeSliceAlt").textContent = `${altFt.toLocaleString()} ft`;
  const targetAltEl = document.getElementById("tbTargetAlt");
  if (targetAltEl) targetAltEl.textContent = `${altFt.toLocaleString()} ft`;

  clearTimeout(_altSliceDebounceTimer);
  _altSliceDebounceTimer = setTimeout(() => {
    fetchHorizontalSlice();
    fetchRadialProfile(); // Synchronize vertical cross-section with interactive altitude slice
  }, 80);
}

function onRadialBearingInput(val) {
  const bearing = parseInt(val, 10);
  const formatted = bearing.toString().padStart(3, "0") + "°";
  document.getElementById("radialBearingVal").textContent = formatted;
  document.getElementById("profBearingTitle").textContent = formatted;
  const targetBearingEl = document.getElementById("tbTargetBearing");
  if (targetBearingEl) targetBearingEl.textContent = formatted;
  updateMapLayers();
  fetchRadialProfile();
}

async function calculateCoverage() {
  showLoading(true);
  updateMapLayers();

  try {
    // 1. Fetch Horizontal Slice at current alt
    await fetchHorizontalSlice();

    // 2. Fetch Radial Profile at current bearing
    await fetchRadialProfile();

    // 3. If Volumetric / 3D Tab or Sweep requested
    fetch3DPointCloud();

    if (document.getElementById("enableFreqSweep").checked) {
      fetchVolumetricCubesSweep();
    }
  } catch (err) {
    console.error("Error calculating coverage:", err);
  } finally {
    showLoading(false);
  }
}

async function fetchHorizontalSlice() {
  const txLat = parseFloat(document.getElementById("txLat").value);
  const txLon = parseFloat(document.getElementById("txLon").value);
  const txAltFt = parseFloat(document.getElementById("txAltFt").value);
  const txAltM = parseFloat(document.getElementById("txAltM").value);
  const rangeKm = parseFloat(document.getElementById("rangeKm").value);
  const altFt = parseFloat(document.getElementById("altSliceFt").value);
  const freqMhz = parseFloat(document.getElementById("freqMhz").value);
  const kFactor = parseFloat(document.getElementById("kFactor").value);

  try {
    const res = await fetch("/api/horizontal-slice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tx_lat: txLat,
        tx_lon: txLon,
        tx_alt_amsl_ft: txAltFt,
        tx_alt_amsl_m: txAltM,
        alt_ft: altFt,
        frequency_hz: freqMhz * 1e6,
        max_range_km: rangeKm,
        num_radials: 72,
        k_factor: kFactor,
        ignored_obstacle_radius_m: getIgnoredObstacleRadiusM()
      })
    });
    activeHorizontalData = await res.json();

    // Update Badge
    document.getElementById("badgeCoveragePct").textContent = `${activeHorizontalData.coverage_pct}%`;

    // Render coverage polygon on map
    if (coveragePolygonLayer) map.removeLayer(coveragePolygonLayer);
    coveragePolygonLayer = L.geoJSON(activeHorizontalData.geojson, {
      style: {
        color: "#22c55e",
        weight: 2.5,
        fillColor: "#22c55e",
        fillOpacity: 0.25
      }
    }).addTo(map);

  } catch (err) {
    console.error("Horizontal slice fetch error:", err);
  }
}

async function fetchRadialProfile() {
  const txLat = parseFloat(document.getElementById("txLat").value);
  const txLon = parseFloat(document.getElementById("txLon").value);
  const txAltFt = parseFloat(document.getElementById("txAltFt").value);
  const txAltM = parseFloat(document.getElementById("txAltM").value);
  const rangeKm = parseFloat(document.getElementById("rangeKm").value);
  const bearing = parseFloat(document.getElementById("radialBearing").value);
  const altFt = parseFloat(document.getElementById("altSliceFt").value);
  const freqMhz = parseFloat(document.getElementById("freqMhz").value);
  const kFactor = parseFloat(document.getElementById("kFactor").value);

  try {
    const res = await fetch("/api/radial-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tx_lat: txLat,
        tx_lon: txLon,
        tx_alt_amsl_ft: txAltFt,
        tx_alt_amsl_m: txAltM,
        bearing_deg: bearing,
        max_distance_km: rangeKm,
        target_alt_amsl_ft: altFt,
        target_alt_amsl_m: altFt * 0.3048,
        frequency_hz: freqMhz * 1e6,
        k_factor: kFactor,
        ignored_obstacle_radius_m: getIgnoredObstacleRadiusM()
      })
    });
    activeRadialData = await res.json();

    // Update Summary Metrics
    updatePathStats(activeRadialData);

    // Draw on Canvas
    drawRadialProfileCanvas(activeRadialData);

    // Update Technology Budget
    renderTechnologyBudgetTab();
  } catch (err) {
    console.error("Radial profile fetch error:", err);
  }
}

function updatePathStats(data) {
  if (!data) return;
  const isOptical = data.optical_los;
  const isRadio = data.radio_los;
  const blk = data.blockage;
  const isBlocked = !isOptical || !isRadio || (blk != null);

  const losEl = document.getElementById("statLosStatus");
  if (isOptical && isRadio) {
    losEl.textContent = "CLEAR LOS";
    losEl.style.color = "var(--accent-green)";
  } else if (!isOptical) {
    losEl.textContent = "TERRAIN BLOCKED";
    losEl.style.color = "#ef4444";
  } else {
    losEl.textContent = "FRESNEL BLOCKED";
    losEl.style.color = "#f59e0b";
  }

  // Update Blockage Distance Stat Box & Title Badge
  const blkBoxVal = document.getElementById("statBlockageDist");
  const badgeEl = document.getElementById("profBlockageBadge");

  if (isBlocked && (blk || data.critical_obstacle)) {
    const distKm = blk ? blk.distance_km : data.critical_obstacle.distance_km;
    const penM = (blk && blk.penetration_m !== undefined) ? blk.penetration_m : (data.critical_obstacle ? -data.critical_obstacle.clearance_m : 0);

    if (blkBoxVal) {
      blkBoxVal.innerHTML = `<span style="color:#ef4444; font-weight:800; font-size:14px;">${distKm.toFixed(2)} km</span>`;
    }

    if (badgeEl) {
      badgeEl.style.display = "inline-block";
      if (!isOptical) {
        badgeEl.style.background = "rgba(239, 68, 68, 0.2)";
        badgeEl.style.color = "#ef4444";
        badgeEl.style.border = "1px solid rgba(239, 68, 68, 0.4)";
        badgeEl.textContent = `⛔ Terrain Blockage at ${distKm.toFixed(2)} km (${penM > 0 ? penM.toFixed(1) + ' m penetration' : 'clearance <= 0'})`;
      } else {
        badgeEl.style.background = "rgba(245, 158, 11, 0.2)";
        badgeEl.style.color = "#f59e0b";
        badgeEl.style.border = "1px solid rgba(245, 158, 11, 0.4)";
        badgeEl.textContent = `⚠️ Fresnel Obstruction at ${distKm.toFixed(2)} km`;
      }
    }
  } else {
    if (blkBoxVal) {
      blkBoxVal.innerHTML = `<span style="color:var(--accent-green); font-weight:700;">NONE (CLEAR)</span>`;
    }
    if (badgeEl) {
      badgeEl.style.display = "inline-block";
      badgeEl.style.background = "rgba(34, 197, 94, 0.15)";
      badgeEl.style.color = "var(--accent-green)";
      badgeEl.style.border = "1px solid rgba(34, 197, 94, 0.4)";
      badgeEl.textContent = `✔ Clear Line of Sight (${data.distance_km.toFixed(1)} km)`;
    }
  }

  document.getElementById("statMinClearance").textContent = `${data.min_clearance_m} m`;

  const freqKey = Object.keys(data.frequencies)[0];
  const fData = data.frequencies[freqKey];
  if (fData) {
    document.getElementById("statFresnelRatio").textContent = `${fData.fresnel_clearance_ratio}`;
    document.getElementById("statDiffLoss").textContent = `${fData.diffraction_loss_db} dB`;
    document.getElementById("statFspl").textContent = `${fData.fspl_db} dB`;
    document.getElementById("statTotalLoss").textContent = `${fData.total_path_loss_db} dB`;
  }
}

async function fetch3DPointCloud() {
  const txLat = parseFloat(document.getElementById("txLat").value);
  const txLon = parseFloat(document.getElementById("txLon").value);
  const txAltFt = parseFloat(document.getElementById("txAltFt").value);
  const txAltM = parseFloat(document.getElementById("txAltM").value);
  const rangeKm = parseFloat(document.getElementById("rangeKm").value);
  const minAltFt = parseFloat(document.getElementById("minAltFt").value);
  const maxAltFt = parseFloat(document.getElementById("maxAltFt").value);
  const freqMhz = parseFloat(document.getElementById("freqMhz").value);
  const kFactor = parseFloat(document.getElementById("kFactor").value);

  try {
    const res = await fetch("/api/3d-point-cloud", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tx_lat: txLat,
        tx_lon: txLon,
        tx_alt_amsl_ft: txAltFt,
        tx_alt_amsl_m: txAltM,
        max_range_km: Math.min(rangeKm, 100),
        min_alt_ft: minAltFt,
        max_alt_ft: maxAltFt,
        frequency_hz: freqMhz * 1e6,
        num_radials: 36,
        range_step_km: 4.0,
        k_factor: kFactor,
        ignored_obstacle_radius_m: getIgnoredObstacleRadiusM()
      })
    });
    const cloud = await res.json();
    renderThreeCubes(cloud.points);
  } catch (err) {
    console.error("3D point cloud fetch error:", err);
  }
}

async function fetchVolumetricCubesSweep() {
  const txLat = parseFloat(document.getElementById("txLat").value);
  const txLon = parseFloat(document.getElementById("txLon").value);
  const txAltFt = parseFloat(document.getElementById("txAltFt").value);
  const txAltM = parseFloat(document.getElementById("txAltM").value);
  const rangeKm = parseFloat(document.getElementById("rangeKm").value);
  const minAltFt = parseFloat(document.getElementById("minAltFt").value);
  const maxAltFt = parseFloat(document.getElementById("maxAltFt").value);
  const minMhz = parseFloat(document.getElementById("sweepMinMhz").value);
  const maxMhz = parseFloat(document.getElementById("sweepMaxMhz").value);
  const stepMhz = parseFloat(document.getElementById("sweepStepMhz").value);
  const kFactor = parseFloat(document.getElementById("kFactor").value);

  try {
    const res = await fetch("/api/volumetric-cubes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tx_lat: txLat,
        tx_lon: txLon,
        tx_alt_amsl_ft: txAltFt,
        tx_alt_amsl_m: txAltM,
        max_range_km: Math.min(rangeKm, 120),
        min_alt_ft: minAltFt,
        max_alt_ft: maxAltFt,
        freq_min_hz: minMhz * 1e6,
        freq_max_hz: maxMhz * 1e6,
        freq_step_hz: stepMhz * 1e6,
        num_radials: 36,
        k_factor: kFactor,
        ignored_obstacle_radius_m: getIgnoredObstacleRadiusM()
      })
    });
    const sweepData = await res.json();
    renderSweepTable(sweepData.frequency_sweep_comparison);
    drawSweepChart(sweepData.frequency_sweep_comparison);
  } catch (err) {
    console.error("Sweep fetch error:", err);
  }
}

/* =========================================================================
   4. 2D CANVAS DRAWING (VERTICAL RADIAL PROFILE)
   ========================================================================= */
function drawRadialProfileCanvas(data) {
  const canvas = document.getElementById("radialProfileCanvas");
  if (!canvas || !data || !data.profile) return;

  const prof = data.profile;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 800;
  const h = 340;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const FT = 3.28084;
  const dists = prof.distances_km;
  const maxDist = dists[dists.length - 1] || 100.0;

  // Use altitude in feet across the entire visualizer
  const terrFt = prof.terrain_elev_ft || prof.terrain_elev_m.map(m => m * FT);
  const effTerrFt = prof.effective_terrain_ft || prof.effective_terrain_m.map(m => m * FT);
  const rayFt = prof.los_ray_ft || prof.los_ray_m.map(m => m * FT);
  const fresnelFt = prof.fresnel_bottom_ft || prof.fresnel_bottom_m.map(m => m * FT);
  const txAltFt = data.tx.alt_amsl_ft !== undefined ? data.tx.alt_amsl_ft : (data.tx.alt_amsl_m * FT);
  const rxAltFt = data.rx.alt_amsl_ft !== undefined ? data.rx.alt_amsl_ft : (data.rx.alt_amsl_m * FT);

  const allAltitudesFt = [
    ...effTerrFt,
    ...rayFt,
    ...fresnelFt,
    txAltFt,
    rxAltFt
  ];
  const minAltFt = Math.max(0, Math.floor(Math.min(...allAltitudesFt) / 1000) * 1000);
  const maxAltFt = Math.ceil((Math.max(...allAltitudesFt) + 1500) / 1000) * 1000;

  const padLeft = 74;
  const padRight = 25;
  const padTop = 24;
  const padBottom = 35;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  function getX(distKm) {
    return padLeft + (distKm / maxDist) * plotW;
  }
  function getY(altFt) {
    return padTop + plotH - ((altFt - minAltFt) / (maxAltFt - minAltFt)) * plotH;
  }

  canvas._profilePlotData = {
    prof: prof,
    data: data,
    maxDist: maxDist,
    minAltFt: minAltFt,
    maxAltFt: maxAltFt,
    terrFt: terrFt,
    effTerrFt: effTerrFt,
    rayFt: rayFt,
    fresnelFt: fresnelFt,
    padLeft: padLeft,
    plotW: plotW,
    padTop: padTop,
    plotH: plotH
  };

  // 1. Grid Lines (in feet AMSL)
  ctx.font = "10px sans-serif";
  ctx.fillStyle = "#94a3b8";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  const numAltSteps = 5;
  for (let i = 0; i <= numAltSteps; i++) {
    const aVal = minAltFt + (i / numAltSteps) * (maxAltFt - minAltFt);
    const y = getY(aVal);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);
    ctx.stroke();

    ctx.fillText(`${Math.round(aVal).toLocaleString()} ft`, padLeft - 8, y);
  }

  // Label at top of Y-axis
  ctx.fillStyle = "#38bdf8";
  ctx.font = "bold 9.5px sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("Altitude (ft AMSL)", padLeft, padTop - 10);

  // Distance Ticks
  ctx.font = "10px sans-serif";
  ctx.fillStyle = "#94a3b8";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= 5; i++) {
    const dVal = (i / 5) * maxDist;
    const x = getX(dVal);
    ctx.fillText(`${Math.round(dVal)} km`, x, padTop + plotH + 8);
  }

  // 2. Draw Terrain Cross-Section (with slate fill)
  ctx.beginPath();
  ctx.moveTo(getX(dists[0]), padTop + plotH);
  for (let i = 0; i < dists.length; i++) {
    ctx.lineTo(getX(dists[i]), getY(terrFt[i]));
  }
  ctx.lineTo(getX(dists[dists.length - 1]), padTop + plotH);
  ctx.closePath();
  ctx.fillStyle = "#334155";
  ctx.fill();

  // 3. Draw Effective Terrain (Terrain + Earth Bulge)
  ctx.beginPath();
  for (let i = 0; i < dists.length; i++) {
    const x = getX(dists[i]);
    const y = getY(effTerrFt[i]);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "#eab308";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 3]);
  ctx.stroke();
  ctx.setLineDash([]);

  // 4. Draw 1st Fresnel Zone Bottom Envelope
  ctx.beginPath();
  for (let i = 0; i < dists.length; i++) {
    const x = getX(dists[i]);
    const y = getY(fresnelFt[i]);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // 5. Draw Direct LOS Ray
  const x0 = getX(0);
  const y0 = getY(txAltFt);
  const xEnd = getX(maxDist);
  const yEnd = getY(rxAltFt);

  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(xEnd, yEnd);
  ctx.strokeStyle = "#8b5cf6";
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // 6. Tx and Rx Endpoint dots
  ctx.fillStyle = "#38bdf8";
  ctx.beginPath();
  ctx.arc(x0, y0, 5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#f59e0b";
  ctx.beginPath();
  ctx.arc(xEnd, yEnd, 5, 0, Math.PI * 2);
  ctx.fill();

  // Rx Target Altitude Callout above Rx Dot (in feet)
  ctx.font = "bold 10px sans-serif";
  ctx.fillStyle = "#f59e0b";
  ctx.textAlign = "right";
  ctx.fillText(`Target: ${Math.round(rxAltFt).toLocaleString()} ft AMSL`, xEnd, Math.max(padTop + 14, yEnd - 8));

  // 6b. Compound Mast Mask Indicator (Tolerance for EU-DEM / Compound Obstacles)
  const ignoredRadiusM = data.ignored_obstacle_radius_m || 0;
  if (ignoredRadiusM > 0) {
    const xComp = getX(ignoredRadiusM / 1000.0);
    const bandW = Math.max(3, xComp - padLeft);
    ctx.save();
    ctx.fillStyle = "rgba(6, 182, 212, 0.12)";
    ctx.fillRect(padLeft, padTop, bandW, plotH);
    ctx.strokeStyle = "rgba(6, 182, 212, 0.6)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(padLeft + bandW, padTop);
    ctx.lineTo(padLeft + bandW, padTop + plotH);
    ctx.stroke();
    ctx.fillStyle = "#06b6d4";
    ctx.font = "9px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(`Compound Mask (${Math.round(ignoredRadiusM)}m / ${Math.round(ignoredRadiusM * FT)}ft)`, padLeft + 4, padTop + 14);
    ctx.restore();
  }

  // 7. Draw Blockage / Obstacle Callout at Exact Distance
  const blk = data.blockage;
  const isOptical = data.optical_los;
  const isRadio = data.radio_los;
  const isBlocked = !isOptical || !isRadio || (blk != null);

  if (isBlocked && (blk || data.critical_obstacle)) {
    const blkDistKm = blk ? blk.distance_km : data.critical_obstacle.distance_km;
    const xBlk = getX(blkDistKm);

    // Find the closest point in profile to get effective terrain elevation at blockage (in feet)
    let closestElevFt = 0;
    let minDiff = Infinity;
    for (let i = 0; i < dists.length; i++) {
      const diff = Math.abs(dists[i] - blkDistKm);
      if (diff < minDiff) {
        minDiff = diff;
        closestElevFt = effTerrFt[i];
      }
    }
    const yBlkTerrain = getY(closestElevFt);

    // A. Vertical Dashed Danger Line from top to bottom through the blockage
    ctx.save();
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = !isOptical ? "#ef4444" : "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(xBlk, padTop);
    ctx.lineTo(xBlk, padTop + plotH);
    ctx.stroke();
    ctx.restore();

    // B. Blockage Marker Dot (red/amber with outer ring)
    ctx.beginPath();
    ctx.arc(xBlk, yBlkTerrain, 6, 0, Math.PI * 2);
    ctx.fillStyle = !isOptical ? "#ef4444" : "#f59e0b";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();

    // C. Exact Distance Callout Flag
    const penFt = (blk && blk.penetration_ft !== undefined) ? blk.penetration_ft : ((blk && blk.penetration_m !== undefined) ? blk.penetration_m * FT : 0);
    const flagTitle = !isOptical
      ? `⛔ BLOCKAGE: ${blkDistKm.toFixed(2)} km`
      : `⚠️ FRESNEL OBSTACLE: ${blkDistKm.toFixed(2)} km`;
    const flagSub = !isOptical
      ? `Penetration: ${Math.max(0, penFt).toFixed(0)} ft · Elev: ${Math.round(closestElevFt).toLocaleString()} ft AMSL`
      : `Clearance: ${(data.critical_obstacle ? data.critical_obstacle.clearance_m * FT : 0).toFixed(0)} ft · Elev: ${Math.round(closestElevFt).toLocaleString()} ft AMSL`;

    ctx.font = "bold 11px sans-serif";
    const w1 = ctx.measureText(flagTitle).width;
    ctx.font = "9.5px sans-serif";
    const w2 = ctx.measureText(flagSub).width;
    const boxW = Math.max(w1, w2) + 20;
    const boxH = 34;

    let flagX = xBlk - boxW / 2;
    if (flagX < padLeft + 4) flagX = padLeft + 4;
    if (flagX + boxW > w - padRight - 4) flagX = w - padRight - 4 - boxW;

    let flagY = yBlkTerrain - boxH - 12;
    if (flagY < padTop + 4) flagY = padTop + 8;
    if (flagY + boxH > padTop + plotH - 4) flagY = padTop + plotH - boxH - 6;

    // Draw Flag Box
    ctx.save();
    ctx.fillStyle = "rgba(11, 19, 41, 0.94)";
    ctx.shadowColor = !isOptical ? "rgba(239, 68, 68, 0.5)" : "rgba(245, 158, 11, 0.5)";
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.roundRect(flagX, flagY, boxW, boxH, 6);
    ctx.fill();
    ctx.restore();

    ctx.lineWidth = 1.5;
    ctx.strokeStyle = !isOptical ? "#ef4444" : "#f59e0b";
    ctx.beginPath();
    ctx.roundRect(flagX, flagY, boxW, boxH, 6);
    ctx.stroke();

    // Text in flag
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.font = "bold 10.5px sans-serif";
    ctx.fillStyle = !isOptical ? "#ef4444" : "#f59e0b";
    ctx.fillText(flagTitle, flagX + boxW / 2, flagY + 4);

    ctx.font = "9px sans-serif";
    ctx.fillStyle = "#cbd5e1";
    ctx.fillText(flagSub, flagX + boxW / 2, flagY + 18);
  }
}

function setupCanvasInteractions() {
  const canvas = document.getElementById("radialProfileCanvas");
  const statsDiv = document.getElementById("profileStats");
  if (!canvas) return;

  canvas.addEventListener("mousemove", (e) => {
    const pData = canvas._profilePlotData;
    if (!pData) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const { prof, data, maxDist, padLeft, plotW, terrFt, effTerrFt, rayFt } = pData;
    const FT = 3.28084;

    if (mouseX < padLeft || mouseX > padLeft + plotW) return;

    const mouseDistKm = ((mouseX - padLeft) / plotW) * maxDist;
    // Find closest index
    let closestIdx = 0;
    let minD = Infinity;
    prof.distances_km.forEach((d, idx) => {
      const diff = Math.abs(d - mouseDistKm);
      if (diff < minD) {
        minD = diff;
        closestIdx = idx;
      }
    });

    const dist = prof.distances_km[closestIdx];
    const tFt = terrFt ? terrFt[closestIdx] : (prof.terrain_elev_m[closestIdx] * FT);
    const etFt = effTerrFt ? effTerrFt[closestIdx] : (prof.effective_terrain_m[closestIdx] * FT);
    const rFt = rayFt ? rayFt[closestIdx] : (prof.los_ray_m[closestIdx] * FT);
    const bFt = etFt - tFt;
    const clearFt = rFt - etFt;

    let blkNote = "";
    if (data && (data.blockage || !data.optical_los || !data.radio_los)) {
      const blkDist = data.blockage ? data.blockage.distance_km : (data.critical_obstacle ? data.critical_obstacle.distance_km : null);
      if (blkDist !== null) {
        const delta = Math.abs(dist - blkDist);
        if (delta < 2.5) {
          blkNote = ` &middot; <span style="color:#ef4444; font-weight:800;">⛔ BLOCKAGE POINT (${blkDist.toFixed(2)} km)</span>`;
        }
      }
    }

    statsDiv.innerHTML = `Distance: <b>${dist} km</b> &middot; Terrain: <b>${Math.round(tFt).toLocaleString()} ft</b> &middot; Bulge: <b>${Math.round(bFt).toLocaleString()} ft</b> &middot; LOS Ray: <b>${Math.round(rFt).toLocaleString()} ft</b> &middot; Clearance: <b style="color:${clearFt >= 0 ? '#22c55e' : '#ef4444'}">${Math.round(clearFt).toLocaleString()} ft</b>${blkNote}`;
  });
}

/* =========================================================================
   5. TRANSCEIVER TECHNOLOGY, LINK BUDGET & SPECTRUM SWEEP
   ========================================================================= */
const TECH_PRESETS = {
  vhf_tactical: { txPowerDbm: 37.0, txGainDbi: 2.0, rxGainDbi: 2.0, rxSensDbm: -113.0, fadeMarginDb: 10.0, name: "Tactical VHF/FM Manpack (5W / -113 dBm)" },
  fm_broadcast: { txPowerDbm: 77.0, txGainDbi: 8.0, rxGainDbi: 0.0, rxSensDbm: -98.0, fadeMarginDb: 12.0, name: "FM Broadcast Station (50 kW / -98 dBm)" },
  air_vhf: { txPowerDbm: 44.0, txGainDbi: 6.0, rxGainDbi: 2.0, rxSensDbm: -107.0, fadeMarginDb: 10.0, name: "Aviation VHF AM Voice / Tower (25W / -107 dBm)" },
  tetra_pmr: { txPowerDbm: 40.0, txGainDbi: 6.0, rxGainDbi: 2.0, rxSensDbm: -115.0, fadeMarginDb: 10.0, name: "PMR / TETRA Public Safety (10W / -115 dBm)" },
  lora_iot: { txPowerDbm: 14.0, txGainDbi: 3.0, rxGainDbi: 3.0, rxSensDbm: -137.0, fadeMarginDb: 8.0, name: "LoRaWAN / IoT 868 MHz (25mW / -137 dBm)" },
  adsb_radar: { txPowerDbm: 54.0, txGainDbi: 12.0, rxGainDbi: 3.0, rxSensDbm: -90.0, fadeMarginDb: 10.0, name: "ADS-B / SSR Transponder (250W / -90 dBm)" },
  cellular_5g: { txPowerDbm: 53.0, txGainDbi: 24.0, rxGainDbi: 0.0, rxSensDbm: -98.0, fadeMarginDb: 12.0, name: "5G Sub-6 Massive MIMO Macro (200W / -98 dBm)" },
  wifi6e: { txPowerDbm: 23.0, txGainDbi: 4.0, rxGainDbi: 2.0, rxSensDbm: -82.0, fadeMarginDb: 10.0, name: "WiFi 6E/7 Enterprise AP (200mW / -82 dBm)" },
  microwave_backhaul: { txPowerDbm: 30.0, txGainDbi: 36.0, rxGainDbi: 36.0, rxSensDbm: -80.0, fadeMarginDb: 15.0, name: "Microwave Dish Backhaul (1W / 36dBi / -80 dBm)" },
  sat_terminal: { txPowerDbm: 36.0, txGainDbi: 34.0, rxGainDbi: 34.0, rxSensDbm: -95.0, fadeMarginDb: 8.0, name: "Ku-Band Satellite Terminal (4W / -95 dBm)" }
};

let currentSweepItems = null;

function onTechPresetChange() {
  const sel = document.getElementById("techPresetSelect");
  if (!sel || sel.value === "custom") return;
  const p = TECH_PRESETS[sel.value];
  if (!p) return;

  document.getElementById("linkTxPowerDbm").value = p.txPowerDbm;
  document.getElementById("linkTxGainDbi").value = p.txGainDbi;
  document.getElementById("linkRxGainDbi").value = p.rxGainDbi;
  document.getElementById("linkRxSensDbm").value = p.rxSensDbm;
  document.getElementById("linkFadeMarginDb").value = p.fadeMarginDb;

  onLinkBudgetInput();
}

function onLinkBudgetInput() {
  const txP = parseFloat(document.getElementById("linkTxPowerDbm").value) || 0;
  const txG = parseFloat(document.getElementById("linkTxGainDbi").value) || 0;
  const rxG = parseFloat(document.getElementById("linkRxGainDbi").value) || 0;
  const rxS = parseFloat(document.getElementById("linkRxSensDbm").value) || -100;
  const fade = parseFloat(document.getElementById("linkFadeMarginDb").value) || 0;

  // Watts = 10^((dBm - 30)/10)
  const watts = Math.pow(10, (txP - 30.0) / 10.0);
  let wattsStr = "";
  if (watts >= 1000.0) wattsStr = `= ${(watts / 1000.0).toFixed(1)} kW`;
  else if (watts >= 1.0) wattsStr = `= ${watts.toFixed(1)} W`;
  else if (watts >= 0.001) wattsStr = `= ${(watts * 1000.0).toFixed(1)} mW`;
  else wattsStr = `= ${(watts * 1e6).toFixed(1)} µW`;
  document.getElementById("linkTxWattsLabel").textContent = wattsStr;

  // Maximum Allowable Path Loss: MAPL = Tx_P + Tx_G + Rx_G - Rx_S - Fade_Margin
  const mapl = txP + txG + rxG - rxS - fade;
  document.getElementById("statMaplValue").textContent = `${mapl.toFixed(1)} dB`;

  // Re-render sweep table and chart if data is present
  if (currentSweepItems) {
    renderSweepTable(currentSweepItems);
    drawSweepChart(currentSweepItems);
  }

  // Update sidebar link budget display in real time
  updateSidebarLinkBudgetMetrics();
}

function getMapl() {
  const txP = parseFloat(document.getElementById("linkTxPowerDbm")?.value) || 54.0;
  const txG = parseFloat(document.getElementById("linkTxGainDbi")?.value) || 12.0;
  const rxG = parseFloat(document.getElementById("linkRxGainDbi")?.value) || 3.0;
  const rxS = parseFloat(document.getElementById("linkRxSensDbm")?.value) || -90.0;
  const fade = parseFloat(document.getElementById("linkFadeMarginDb")?.value) || 10.0;
  return txP + txG + rxG - rxS - fade;
}

function renderSweepTable(items) {
  currentSweepItems = items;
  const tbody = document.getElementById("sweepTableBody");
  if (!tbody || !items) return;
  tbody.innerHTML = "";

  const mapl = getMapl();

  items.forEach(item => {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid rgba(255, 255, 255, 0.05)";

    const freqMhz = Math.round(item.freq_hz / 1e6);
    const lamM = 299792458 / item.freq_hz;
    const lamStr = lamM >= 1.0 ? `${lamM.toFixed(2)} m` : `${(lamM * 100).toFixed(1)} cm`;
    const loss = item.avg_path_loss_db;
    const margin = Math.round((mapl - loss) * 10) / 10;
    const linkOk = margin >= 0.0;

    tr.innerHTML = `
      <td style="padding:6px; font-weight:700; color:#fff;">${freqMhz} MHz</td>
      <td style="padding:6px; color:var(--text-muted);">${lamStr}</td>
      <td style="padding:6px; color:var(--accent-cyan); font-weight:600;">${loss} dB</td>
      <td style="padding:6px; color:#f43f5e; font-weight:600;">${mapl.toFixed(1)} dB</td>
      <td style="padding:6px; font-weight:700; color:${linkOk ? '#22c55e' : '#ef4444'};">
        ${linkOk ? `+${margin}` : margin} dB
      </td>
      <td style="padding:6px;">
        <span style="font-size:10px; font-weight:700; background:${linkOk ? 'rgba(34,197,94,0.18)' : 'rgba(239,68,68,0.18)'}; color:${linkOk ? '#22c55e' : '#ef4444'}; padding:3px 7px; border-radius:4px; border:1px solid ${linkOk ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)'};">
          ${linkOk ? '✔ LINK OK' : '✖ OUT OF RANGE'}
        </span>
      </td>
      <td style="padding:6px; color:var(--accent-green); font-weight:700;">${item.coverage_pct}%</td>
    `;
    tbody.appendChild(tr);
  });
}

function drawSweepChart(items) {
  const canvas = document.getElementById("sweepChartCanvas");
  if (!canvas || !items || items.length < 2) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 700;
  const h = 260;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);

  const padLeft = 60;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 35;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  const freqs = items.map(it => it.freq_hz / 1e6);
  const minF = Math.min(...freqs);
  const maxF = Math.max(...freqs);

  const mapl = getMapl();
  const losses = items.map(it => it.avg_path_loss_db);
  const allY = [...losses, mapl];
  const minLoss = Math.min(...allY) - 8;
  const maxLoss = Math.max(...allY) + 8;

  function getX(f) { return padLeft + ((f - minF) / (maxF - minF)) * plotW; }
  function getY(l) { return padTop + plotH - ((l - minLoss) / (maxLoss - minLoss)) * plotH; }

  // 1. Grid
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
  ctx.lineWidth = 1;
  ctx.font = "10px sans-serif";
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i <= 5; i++) {
    const yVal = minLoss + (i / 5) * (maxLoss - minLoss);
    const yPx = getY(yVal);
    ctx.beginPath();
    ctx.moveTo(padLeft, yPx);
    ctx.lineTo(padLeft + plotW, yPx);
    ctx.stroke();
    ctx.fillText(`${Math.round(yVal)} dB`, padLeft - 6, yPx);
  }

  // Frequency Axis Labels
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const fSteps = Math.min(items.length, 6);
  for (let i = 0; i < fSteps; i++) {
    const it = items[Math.floor(i * (items.length - 1) / (fSteps - 1))];
    const fVal = it.freq_hz / 1e6;
    const xPx = getX(fVal);
    ctx.fillText(`${Math.round(fVal)} MHz`, xPx, padTop + plotH + 8);
  }

  // 2. MAPL Limit Threshold Line (Red Dashed)
  const maplY = getY(mapl);
  ctx.save();
  ctx.setLineDash([5, 5]);
  ctx.strokeStyle = "#f43f5e";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(padLeft, maplY);
  ctx.lineTo(padLeft + plotW, maplY);
  ctx.stroke();
  ctx.restore();

  // MAPL Label
  ctx.fillStyle = "#f43f5e";
  ctx.font = "bold 10px sans-serif";
  ctx.textAlign = "right";
  ctx.fillText(`MAPL Limit: ${mapl.toFixed(1)} dB`, padLeft + plotW, maplY - 14);

  // 3. Path Loss Line
  ctx.beginPath();
  items.forEach((it, idx) => {
    const x = getX(it.freq_hz / 1e6);
    const y = getY(it.avg_path_loss_db);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Dots
  items.forEach(it => {
    const x = getX(it.freq_hz / 1e6);
    const y = getY(it.avg_path_loss_db);
    const isOk = it.avg_path_loss_db <= mapl;
    ctx.fillStyle = isOk ? "#22c55e" : "#ef4444";
    ctx.beginPath();
    ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });
}

/* =========================================================================
   6. UTILITIES & MODAL
   ========================================================================= */
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));

  const targetPanel = document.getElementById(tabId);
  if (targetPanel) targetPanel.classList.add("active");

  const evtBtn = event ? event.currentTarget : null;
  if (evtBtn) evtBtn.classList.add("active");

  if (tabId === "mapTab" && map) {
    setTimeout(() => map.invalidateSize(), 100);
  } else if (tabId === "threeTab") {
    setTimeout(() => onWindowResize(), 100);
  } else if (tabId === "techBudgetTab") {
    renderTechnologyBudgetTab();
  } else if (tabId === "sweepTab" && currentSweepItems) {
    setTimeout(() => drawSweepChart(currentSweepItems), 100);
  }
}

function showLoading(show) {
  const el = document.getElementById("loadingOverlay");
  if (el) el.style.display = show ? "flex" : "none";
}

function destinationPoint(lat, lon, bearingDeg, distanceM) {
  const R = 6371000.0;
  const delta = distanceM / R;
  const theta = (bearingDeg * Math.PI) / 180.0;
  const phi1 = (lat * Math.PI) / 180.0;
  const lam1 = (lon * Math.PI) / 180.0;

  const sinPhi2 = Math.sin(phi1) * Math.cos(delta) + Math.cos(phi1) * Math.sin(delta) * Math.cos(theta);
  const phi2 = Math.asin(sinPhi2);

  const y = Math.sin(theta) * Math.sin(delta) * Math.cos(phi1);
  const x = Math.cos(delta) - Math.sin(phi1) * sinPhi2;
  const lam2 = lam1 + Math.atan2(y, x);

  return {
    lat: (phi2 * 180.0) / Math.PI,
    lon: (((lam2 * 180.0) / Math.PI + 540.0) % 360.0) - 180.0
  };
}

/* =========================================================================
   7. RF PHYSICS & FORMULAS MODAL (KATEX ENHANCED)
   ========================================================================= */
function openLogicModal() {
  const modal = document.getElementById("logicModal");
  if (modal) {
    modal.style.display = "flex";
    if (window.renderMathInElement) {
      renderMathInElement(modal, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false }
        ],
        throwOnError: false
      });
    }
  }
}

function closeLogicModal() {
  const modal = document.getElementById("logicModal");
  if (modal) {
    modal.style.display = "none";
  }
}

function onModalBackdropClick(event) {
  if (event.target && event.target.id === "logicModal") {
    closeLogicModal();
  }
}

// Close modal on Escape key
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeLogicModal();
  }
});

/* =========================================================================
   7. SESSION IMPORT / EXPORT (JSON)
   ========================================================================= */

function exportSessionJson() {
  const txLat = parseFloat(document.getElementById("txLat")?.value) || 47.4211;
  const txLon = parseFloat(document.getElementById("txLon")?.value) || 10.9853;
  const txAltFt = parseFloat(document.getElementById("txAltFt")?.value) || 9718.0;
  const txAltM = parseFloat(document.getElementById("txAltM")?.value) || Math.round(txAltFt * 0.3048);
  const locPreset = document.getElementById("locationPreset")?.value || "";

  const rangeKm = parseFloat(document.getElementById("rangeKm")?.value) || 100;
  const kFactor = parseFloat(document.getElementById("kFactor")?.value) || 1.333;
  const compoundMaskEnabled = document.getElementById("toggleCompoundMask") ? document.getElementById("toggleCompoundMask").checked : true;
  const compoundRadiusM = parseFloat(document.getElementById("compoundRadiusM")?.value) || 50;

  const techSystem = activeTechProfileKey || document.getElementById("techSystemSelect")?.value || "SSR_RADAR";
  const freqMhz = parseFloat(document.getElementById("freqMhz")?.value) || 1090.0;

  const sweepEnabled = document.getElementById("enableFreqSweep") ? document.getElementById("enableFreqSweep").checked : false;
  const sweepMin = parseFloat(document.getElementById("sweepMinMhz")?.value) || 100;
  const sweepMax = parseFloat(document.getElementById("sweepMaxMhz")?.value) || 2000;
  const sweepStep = parseFloat(document.getElementById("sweepStepMhz")?.value) || 300;

  const minAltFt = parseFloat(document.getElementById("minAltFt")?.value) || 1000;
  const maxAltFt = parseFloat(document.getElementById("maxAltFt")?.value) || 25000;

  const altSliceFt = parseFloat(document.getElementById("altSliceFt")?.value) || 8000;
  const radialBearing = parseFloat(document.getElementById("radialBearing")?.value) || 225;

  const threeMaxAlt = parseFloat(document.getElementById("threeMaxAltSlider")?.value) || 20000;
  const threeZScale = parseFloat(document.getElementById("threeZScale")?.value) || 5;
  const threeShowBlocked = document.getElementById("threeShowBlocked") ? document.getElementById("threeShowBlocked").checked : false;

  const customBudget = {
    tx_power_dbm: parseFloat(document.getElementById("linkTxPowerDbm")?.value) || 54.0,
    tx_gain_dbi: parseFloat(document.getElementById("linkTxGainDbi")?.value) || 12.0,
    rx_gain_dbi: parseFloat(document.getElementById("linkRxGainDbi")?.value) || 3.0,
    rx_sens_dbm: parseFloat(document.getElementById("linkRxSensDbm")?.value) || -90.0,
    fade_margin_db: parseFloat(document.getElementById("linkFadeMarginDb")?.value) || 10.0,
    tech_preset: document.getElementById("techPresetSelect")?.value || "ssr_interrogator"
  };

  const session = {
    schema: "radiocov-session-v1",
    timestamp: new Date().toISOString(),
    session_name: `RadioCov_${techSystem}_${Math.round(freqMhz)}MHz_${Math.round(rangeKm)}km`,
    transmitter: {
      lat: txLat,
      lon: txLon,
      alt_amsl_ft: txAltFt,
      alt_amsl_m: txAltM,
      location_preset: locPreset
    },
    propagation: {
      max_range_km: rangeKm,
      k_factor: kFactor,
      compound_mask_enabled: compoundMaskEnabled,
      ignored_obstacle_radius_m: compoundRadiusM
    },
    technology: {
      system_key: techSystem,
      channel_index: typeof activeChannelIdx === "number" ? activeChannelIdx : 0,
      freq_mhz: freqMhz,
      channel_overrides: { ...channelParamOverrides },
      custom_budget: customBudget
    },
    sweep: {
      enabled: sweepEnabled,
      min_mhz: sweepMin,
      max_mhz: sweepMax,
      step_mhz: sweepStep
    },
    airspace_grid: {
      min_alt_ft: minAltFt,
      max_alt_ft: maxAltFt
    },
    slices: {
      alt_slice_ft: altSliceFt,
      radial_bearing_deg: radialBearing
    },
    view_3d: {
      max_alt_ft: threeMaxAlt,
      z_scale: threeZScale,
      show_blocked: threeShowBlocked
    }
  };

  const jsonStr = JSON.stringify(session, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const filename = `${session.session_name}_${new Date().toISOString().slice(0, 10)}.json`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast(`Session exported to ${filename}`, "success");
}

function triggerImportSession() {
  const fileInput = document.getElementById("sessionFileInput");
  if (fileInput) {
    fileInput.value = "";
    fileInput.click();
  }
}

function handleSessionFileSelected(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(evt) {
    try {
      const data = JSON.parse(evt.target.result);
      importSessionData(data);
    } catch (err) {
      console.error("Failed to parse session JSON:", err);
      showToast("Failed to parse session JSON: " + err.message, "error");
    }
  };
  reader.readAsText(file);
}

function importSessionData(data) {
  if (!data || (!data.transmitter && !data.propagation)) {
    throw new Error("Invalid session format: missing transmitter or propagation section.");
  }

  // 1. Transmitter
  if (data.transmitter) {
    if (data.transmitter.lat !== undefined && document.getElementById("txLat")) {
      document.getElementById("txLat").value = data.transmitter.lat;
    }
    if (data.transmitter.lon !== undefined && document.getElementById("txLon")) {
      document.getElementById("txLon").value = data.transmitter.lon;
    }
    if (data.transmitter.alt_amsl_ft !== undefined || data.transmitter.alt_amsl_m !== undefined) {
      const ft = data.transmitter.alt_amsl_ft !== undefined ? data.transmitter.alt_amsl_ft : Math.round(data.transmitter.alt_amsl_m * 3.28084);
      if (document.getElementById("txAltFt")) document.getElementById("txAltFt").value = ft;
      if (document.getElementById("txAltM")) document.getElementById("txAltM").value = Math.round(ft * 0.3048);
    }
    if (data.transmitter.location_preset && document.getElementById("locationPreset")) {
      document.getElementById("locationPreset").value = data.transmitter.location_preset;
    }
    if (txMarker && map && data.transmitter.lat !== undefined && data.transmitter.lon !== undefined) {
      txMarker.setLatLng([data.transmitter.lat, data.transmitter.lon]);
      map.panTo([data.transmitter.lat, data.transmitter.lon]);
    }
  }

  // 2. Propagation & Compound Alignment
  if (data.propagation) {
    if (data.propagation.max_range_km !== undefined && document.getElementById("rangeKm")) {
      document.getElementById("rangeKm").value = data.propagation.max_range_km;
      updateRangeLabel(data.propagation.max_range_km);
    }
    if (data.propagation.k_factor !== undefined && document.getElementById("kFactor")) {
      document.getElementById("kFactor").value = data.propagation.k_factor;
      updateKFactorLabel(data.propagation.k_factor);
    }
    if (data.propagation.compound_mask_enabled !== undefined && document.getElementById("toggleCompoundMask")) {
      document.getElementById("toggleCompoundMask").checked = !!data.propagation.compound_mask_enabled;
    }
    if (data.propagation.ignored_obstacle_radius_m !== undefined && document.getElementById("compoundRadiusM")) {
      document.getElementById("compoundRadiusM").value = data.propagation.ignored_obstacle_radius_m;
    }
    onCompoundMaskToggle(document.getElementById("toggleCompoundMask")?.checked !== false);
    onCompoundRadiusInput(document.getElementById("compoundRadiusM")?.value || 50);
  }

  // 3. Technology System & Channel Link Budget
  if (data.technology) {
    const sysKey = data.technology.system_key;
    if (sysKey && currentTechProfiles[sysKey]) {
      activeTechProfileKey = sysKey;
      const topSel = document.getElementById("techSystemSelect");
      if (topSel) topSel.value = sysKey;
      const sideSel = document.getElementById("techSelectSidebar");
      if (sideSel) sideSel.value = sysKey;
      const tbSel = document.getElementById("tbTechSelect");
      if (tbSel) tbSel.value = sysKey;

      applyTechnologyProfile(sysKey);

      if (typeof data.technology.channel_index === "number") {
        selectTechnologyChannel(data.technology.channel_index);
      }
    }

    if (data.technology.channel_overrides) {
      channelParamOverrides = { ...data.technology.channel_overrides };
    }

    if (data.technology.freq_mhz !== undefined && document.getElementById("freqMhz")) {
      document.getElementById("freqMhz").value = data.technology.freq_mhz;
      onFreqChange();
    }

    if (data.technology.custom_budget) {
      const cb = data.technology.custom_budget;
      if (cb.tx_power_dbm !== undefined && document.getElementById("linkTxPowerDbm")) {
        document.getElementById("linkTxPowerDbm").value = cb.tx_power_dbm;
      }
      if (cb.tx_gain_dbi !== undefined && document.getElementById("linkTxGainDbi")) {
        document.getElementById("linkTxGainDbi").value = cb.tx_gain_dbi;
      }
      if (cb.rx_gain_dbi !== undefined && document.getElementById("linkRxGainDbi")) {
        document.getElementById("linkRxGainDbi").value = cb.rx_gain_dbi;
      }
      if (cb.rx_sens_dbm !== undefined && document.getElementById("linkRxSensDbm")) {
        document.getElementById("linkRxSensDbm").value = cb.rx_sens_dbm;
      }
      if (cb.fade_margin_db !== undefined && document.getElementById("linkFadeMarginDb")) {
        document.getElementById("linkFadeMarginDb").value = cb.fade_margin_db;
      }
      if (cb.tech_preset !== undefined && document.getElementById("techPresetSelect")) {
        document.getElementById("techPresetSelect").value = cb.tech_preset;
      }
      onLinkBudgetInput();
    }
  }

  // 4. Spectrum Sweep
  if (data.sweep) {
    if (data.sweep.enabled !== undefined && document.getElementById("enableFreqSweep")) {
      document.getElementById("enableFreqSweep").checked = !!data.sweep.enabled;
    }
    if (data.sweep.min_mhz !== undefined && document.getElementById("sweepMinMhz")) {
      document.getElementById("sweepMinMhz").value = data.sweep.min_mhz;
    }
    if (data.sweep.max_mhz !== undefined && document.getElementById("sweepMaxMhz")) {
      document.getElementById("sweepMaxMhz").value = data.sweep.max_mhz;
    }
    if (data.sweep.step_mhz !== undefined && document.getElementById("sweepStepMhz")) {
      document.getElementById("sweepStepMhz").value = data.sweep.step_mhz;
    }
    toggleSweepInputs();
  }

  // 5. Airspace Grid
  if (data.airspace_grid) {
    if (data.airspace_grid.min_alt_ft !== undefined && document.getElementById("minAltFt")) {
      document.getElementById("minAltFt").value = data.airspace_grid.min_alt_ft;
    }
    if (data.airspace_grid.max_alt_ft !== undefined && document.getElementById("maxAltFt")) {
      document.getElementById("maxAltFt").value = data.airspace_grid.max_alt_ft;
    }
  }

  // 6. Interactive Slices
  if (data.slices) {
    if (data.slices.alt_slice_ft !== undefined && document.getElementById("altSliceFt")) {
      document.getElementById("altSliceFt").value = data.slices.alt_slice_ft;
      document.getElementById("altSliceVal").textContent = `${parseInt(data.slices.alt_slice_ft, 10).toLocaleString()} ft`;
      document.getElementById("badgeSliceAlt").textContent = `${parseInt(data.slices.alt_slice_ft, 10).toLocaleString()} ft`;
    }
    if (data.slices.radial_bearing_deg !== undefined && document.getElementById("radialBearing")) {
      document.getElementById("radialBearing").value = data.slices.radial_bearing_deg;
      const bFormatted = parseInt(data.slices.radial_bearing_deg, 10).toString().padStart(3, "0") + "°";
      document.getElementById("radialBearingVal").textContent = bFormatted;
      document.getElementById("profBearingTitle").textContent = bFormatted;
    }
  }

  // 7. 3D View Settings
  if (data.view_3d) {
    if (data.view_3d.max_alt_ft !== undefined && document.getElementById("threeMaxAltSlider")) {
      document.getElementById("threeMaxAltSlider").value = data.view_3d.max_alt_ft;
      onThreeMaxAltChange(data.view_3d.max_alt_ft);
    }
    if (data.view_3d.z_scale !== undefined && document.getElementById("threeZScale")) {
      document.getElementById("threeZScale").value = data.view_3d.z_scale;
      updateThreeZScale(data.view_3d.z_scale);
    }
    if (data.view_3d.show_blocked !== undefined && document.getElementById("threeShowBlocked")) {
      document.getElementById("threeShowBlocked").checked = !!data.view_3d.show_blocked;
      toggleThreeBlockedCubes(!!data.view_3d.show_blocked);
    }
  }

  // 8. Re-calculate entire session
  calculateCoverage();

  const name = data.session_name || "Session";
  showToast(`✅ Successfully imported "${name}"`, "success");
}

let _toastTimer = null;
function showToast(msg, type = "info") {
  const toast = document.getElementById("toastNotification");
  if (!toast) return;
  const msgEl = document.getElementById("toastMessage");
  const iconEl = document.getElementById("toastIcon");
  if (msgEl) msgEl.textContent = msg;
  if (iconEl) {
    iconEl.textContent = type === "success" ? "✅" : (type === "error" ? "❌" : "ℹ️");
  }
  toast.style.borderColor = type === "success" ? "var(--accent-green)" : (type === "error" ? "var(--accent-red)" : "var(--accent-cyan)");
  toast.style.display = "flex";
  toast.style.opacity = "1";

  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => { toast.style.display = "none"; }, 300);
  }, 4000);
}
