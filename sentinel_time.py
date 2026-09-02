# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
import os
import json
import webbrowser
import requests

from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, 
                         QgsProject)
from qgis.utils import iface
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                                 QLabel, QDateEdit, QSpinBox, 
                                 QPushButton, QMessageBox, QCheckBox, QTextEdit, QFileDialog, QLineEdit, QAction)
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtGui import QIcon

STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign?href="

def get_canvas_extent_wgs84():
    canvas = iface.mapCanvas()
    extent = canvas.extent()
    canvas_crs = canvas.mapSettings().destinationCrs()
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    if canvas_crs != wgs84:
        transform = QgsCoordinateTransform(canvas_crs, wgs84, QgsProject.instance())
        extent = transform.transformBoundingBox(extent)
    return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())

def search_stac_items(bbox, start_date, end_date):
    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{start_date.isoformat()}T00:00:00Z/{end_date.isoformat()}T23:59:59Z",
        "limit": 500,
        "sortby": [{"field": "properties.datetime", "direction": "asc"}]
    }
    response = requests.post(STAC_SEARCH_URL, json=body, timeout=30)
    response.raise_for_status()
    return response.json().get("features", [])

def get_signed_url(href):
    res = requests.get(f"{SAS_SIGN_URL}{href}", timeout=10)
    res.raise_for_status()
    return res.json().get("href")

class SentinelExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sentinel-2 Rapport & Export HTML Interactif")
        self.setMinimumWidth(520)
        self.date_groups = {}
        self.init_ui()
        self.update_mode()

    def init_ui(self):
        layout = QVBoxLayout()
        
        group_period = QGroupBox("Configuration de la periode et recherche")
        layout_period = QVBoxLayout()
        
        row_start = QHBoxLayout()
        row_start.addWidget(QLabel("Date de debut :"))
        self.date_start = QDateEdit(QDate.currentDate().addYears(-1))
        self.date_start.setCalendarPopup(True)
        self.date_start.dateChanged.connect(self.update_mode)
        row_start.addWidget(self.date_start)
        layout_period.addLayout(row_start)
        
        self.chk_end_date = QCheckBox("Activer la date de fin")
        self.chk_end_date.setChecked(True)
        self.chk_end_date.stateChanged.connect(self.update_mode)
        layout_period.addWidget(self.chk_end_date)
        
        row_end = QHBoxLayout()
        row_end.addWidget(QLabel("Date de fin :"))
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.dateChanged.connect(self.update_mode)
        row_end.addWidget(self.date_end)
        layout_period.addLayout(row_end)
        
        self.chk_step = QCheckBox("Activer le pas en mois (Timelapse)")
        self.chk_step.setChecked(True)
        self.chk_step.stateChanged.connect(self.update_mode)
        layout_period.addWidget(self.chk_step)
        
        row_step = QHBoxLayout()
        row_step.addWidget(QLabel("Pas (en mois) :"))
        self.spin_step = QSpinBox()
        self.spin_step.setRange(1, 24)
        self.spin_step.setValue(3)
        self.spin_step.valueChanged.connect(self.update_mode)
        row_step.addWidget(self.spin_step)
        layout_period.addLayout(row_step)
        
        self.btn_refresh = QPushButton("Rechercher la mosaique complete (toutes dalles)")
        self.btn_refresh.clicked.connect(self.fetch_catalog_data)
        layout_period.addWidget(self.btn_refresh)
        
        self.lbl_mode = QLabel()
        self.lbl_mode.setStyleSheet("color: #125953; font-weight: bold; background: #dcefec; padding: 6px; border-radius: 3px;")
        layout_period.addWidget(self.lbl_mode)
        
        group_period.setLayout(layout_period)
        layout.addWidget(group_period)
        
        group_output = QGroupBox("Dossier de sortie du rapport")
        layout_output = QHBoxLayout()
        self.txt_out_dir = QLineEdit()
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(default_dir):
            default_dir = os.path.expanduser("~")
        self.txt_out_dir.setText(default_dir)
        layout_output.addWidget(self.txt_out_dir)
        
        self.btn_browse = QPushButton("Parcourir...")
        self.btn_browse.clicked.connect(self.browse_directory)
        layout_output.addWidget(self.btn_browse)
        group_output.setLayout(layout_output)
        layout.addWidget(group_output)
        
        group_results = QGroupBox("Dates reelles detectees (Mosaique multi-dalles)")
        layout_results = QVBoxLayout()
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setMinimumHeight(90)
        layout_results.addWidget(self.txt_results)
        group_results.setLayout(layout_results)
        layout.addWidget(group_results)
        
        group_export = QGroupBox("Generation")
        layout_export = QVBoxLayout()
        
        self.btn_html = QPushButton("Generer et ouvrir le rapport HTML interactif")
        self.btn_html.setEnabled(False)
        self.btn_html.setStyleSheet("background-color: #1b7f79; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_html.clicked.connect(self.export_html_slider)
        layout_export.addWidget(self.btn_html)
        
        group_export.setLayout(layout_export)
        layout.addWidget(group_export)
        
        self.setLayout(layout)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de sortie", self.txt_out_dir.text())
        if dir_path:
            self.txt_out_dir.setText(dir_path)

    def update_mode(self):
        has_end = self.chk_end_date.isChecked()
        self.date_end.setEnabled(has_end)
        self.chk_step.setEnabled(has_end)
        has_step = self.chk_step.isChecked() and has_end
        self.spin_step.setEnabled(has_step)
        
        if not has_end:
            self.lbl_mode.setText("Mode : Date unique")
        elif not has_step:
            self.lbl_mode.setText("Mode : Comparaison Avant / Apres")
        else:
            self.lbl_mode.setText("Mode : Timelapse par intervalle mensuel")

    def fetch_catalog_data(self):
        try:
            bbox = get_canvas_extent_wgs84()
            start = self.date_start.date().toPyDate()
            end = self.date_end.date().toPyDate() if self.chk_end_date.isChecked() else start + timedelta(days=1)
            
            all_features = search_stac_items(bbox, start, end)
            if not all_features:
                QMessageBox.warning(self, "Catalogue", "Aucune image trouvee pour cette periode sur l'emprise.")
                return
                
            grouped_raw = {}
            for feat in all_features:
                d_str = feat["properties"]["datetime"][:10]
                if d_str not in grouped_raw:
                    grouped_raw[d_str] = []
                grouped_raw[d_str].append(feat)
                
            available_dates = sorted(list(grouped_raw.keys()))
            
            has_end = self.chk_end_date.isChecked()
            has_step = self.chk_step.isChecked() and has_end
            
            selected_dates = []
            if not has_end:
                selected_dates = [available_dates[0]]
            elif not has_step:
                selected_dates = [available_dates[0], available_dates[-1]]
            else:
                step_months = self.spin_step.value()
                target_date = start
                while target_date <= end:
                    closest_d = min(available_dates, key=lambda d: abs(date.fromisoformat(d) - target_date))
                    if closest_d not in selected_dates:
                        selected_dates.append(closest_d)
                    
                    month = target_date.month - 1 + step_months
                    year = target_date.year + month // 12
                    month = month % 12 + 1
                    day = min(target_date.day, 28)
                    target_date = date(year, month, day)
                selected_dates = sorted(list(set(selected_dates)))

            self.date_groups = {d: grouped_raw[d] for d in selected_dates}

            summary_text = []
            for d in selected_dates:
                dt = datetime.strptime(d, "%Y-%m-%d")
                date_fr = dt.strftime("%d/%m/%Y")
                tiles_count = len(self.date_groups[d])
                summary_text.append(f"- {date_fr} ({tiles_count} dalle(s))")

            self.txt_results.setText(f"{len(selected_dates)} dates de mosaique selectionnees :\n" + "\n".join(summary_text))
            self.btn_html.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def export_html_slider(self):
        if not self.date_groups:
            return
        try:
            out_dir = self.txt_out_dir.text()
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
                
            bbox = get_canvas_extent_wgs84()
            xmin, ymin, xmax, ymax = bbox

            slides_data = []
            for d_str, feats in sorted(self.date_groups.items()):
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                date_fr = dt.strftime("%d/%m/%Y")
                
                item_entries = []
                for feat in feats:
                    item_id = feat["id"]
                    assets = feat.get("assets", {})
                    visual_asset = assets.get("visual")
                    visual_href = get_signed_url(visual_asset["href"]) if visual_asset and "href" in visual_asset else ""
                    
                    item_entries.append({
                        "itemId": item_id,
                        "downloadUrl": visual_href
                    })
                
                if item_entries:
                    slides_data.append({"date": date_fr, "iso": d_str, "items": item_entries})

            slides_json = json.dumps(slides_data, ensure_ascii=False)

            html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Rapport d'Imagerie Sentinel-2 - Mosaique interactive</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
<style>
:root {{
    --bg-main: #0f172a;
    --bg-card: #1e293b;
    --accent: #0ea5e9;
    --accent-hover: #0284c7;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --border: #334155;
}}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-main);
    color: var(--text-main);
    margin: 0;
    padding: 30px 20px;
}}
.wrapper {{
    max-width: 950px;
    margin: 0 auto;
}}
header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-card);
    padding: 20px 30px;
    border-radius: 8px;
    border: 1px solid var(--border);
    margin-bottom: 25px;
}}
.logo-area h1 {{
    margin: 0;
    font-size: 20px;
    color: var(--text-main);
    letter-spacing: -0.5px;
}}
.logo-area p {{
    margin: 4px 0 0 0;
    font-size: 12px;
    color: var(--text-muted);
}}
.badge {{
    background: rgba(14, 165, 233, 0.1);
    color: var(--accent);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid rgba(14, 165, 233, 0.2);
}}
.card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}}
.viewer-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}}
.date-title {{
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
}}
#map {{
    height: 480px;
    border-radius: 6px;
    border: 1px solid var(--border);
    z-index: 1;
}}
.controls {{
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 15px;
}}
input[type=range] {{
    width: 100%;
    accent-color: var(--accent);
    cursor: pointer;
}}
.steps-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 5px;
}}
.step-pill {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}}
.step-pill:hover {{
    border-color: var(--accent);
    color: var(--text-main);
}}
.step-pill.active {{
    background: var(--accent);
    color: white;
    border-color: var(--accent);
}}
.btn {{
    background: var(--accent);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.2s;
    text-decoration: none;
    display: inline-block;
    text-align: center;
}}
.btn:hover {{
    background: var(--accent-hover);
}}
.downloads-section h3 {{
    margin-top: 0;
    font-size: 16px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
}}
.download-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 15px;
}}
.download-item {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    padding: 12px 15px;
    border-radius: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.download-item span {{
    font-size: 13px;
    font-weight: 500;
}}
#statusMsg {{
    margin-top: 15px;
    font-size: 13px;
    color: var(--accent);
    font-weight: 600;
    text-align: center;
}}
footer {{
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 40px;
    border-top: 1px solid var(--border);
    padding-top: 20px;
}}
</style>
</head>
<body>
<div class="wrapper">
  <header>
    <div class="logo-area">
      <h1>Rapport d'Imagerie Satellite</h1>
      <p>Source : Microsoft Planetary Computer (STAC API) — Copernicus Sentinel-2 L2A</p>
    </div>
    <div class="badge">Mosaique Interactive</div>
  </header>

  <div class="card">
    <div class="viewer-header">
      <div style="font-size: 14px; font-weight: 600; color: var(--text-muted);">Visualisation Cartographique</div>
      <div class="date-title" id="dateLabel">--/--/----</div>
    </div>
    
    <div id="map"></div>
    
    <div class="controls">
      <input type="range" id="timeSlider" min="0" max="{len(slides_data) - 1}" value="0" oninput="updateSlide(this.value)">
      <div class="steps-container" id="stepsContainer"></div>
    </div>
  </div>

  <div class="card downloads-section">
    <h3>Centre de Téléchargement Organisé</h3>
    <p style="font-size: 13px; color: var(--text-muted);">Téléchargez chaque date sous forme d'archive ZIP propre (contenant toutes ses dalles).</p>
    
    <div style="margin-bottom: 15px;">
      <button class="btn" onclick="downloadEverythingZip()">Tout télécharger (Archives ZIP séparées)</button>
    </div>

    <div class="download-grid" id="downloadGrid"></div>
    <div id="statusMsg"></div>
  </div>

  <footer>
    Généré automatiquement via QGIS &bull; Données ouvertes Copernicus Sentinel-2
  </footer>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const slides = {slides_json};
let currentLayers = [];

// Initialisation de la carte Leaflet
const map = L.map('map');

// Application exacte de l'emprise visuelle QGIS (Sud-Ouest -> Nord-Est)
const canvasBounds = [
    [{ymin}, {xmin}], // Sud-Ouest [lat, lon]
    [{ymax}, {xmax}]  // Nord-Est [lat, lon]
];
map.fitBounds(canvasBounds);

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 20
}}).addTo(map);

function updateSlide(index) {{
    index = parseInt(index);
    document.getElementById('timeSlider').value = index;
    const slide = slides[index];
    document.getElementById('dateLabel').innerText = slide.date;
    
    document.querySelectorAll('.step-pill').forEach((pill, idx) => {{
        if (idx === index) {{
            pill.classList.add('active');
        }} else {{
            pill.classList.remove('active');
        }}
    }});
    
    currentLayers.forEach(layer => map.removeLayer(layer));
    currentLayers = [];
    
    slide.items.forEach(item => {{
        const tileUrl = `https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item=${{item.itemId}}&assets=visual&asset_bidx=visual%7C1%2C2%2C3&nodata=0&format=png`;
        const tileLayer = L.tileLayer(tileUrl, {{
            attribution: 'Sentinel-2 Copernicus / Microsoft Planetary Computer',
            tileSize: 256,
            minZoom: 0,
            maxZoom: 18
        }});
        tileLayer.addTo(map);
        currentLayers.push(tileLayer);
    }});
}}

function buildStepsContainer() {{
    const container = document.getElementById('stepsContainer');
    container.innerHTML = '';
    slides.forEach((slide, idx) => {{
        const pill = document.createElement('div');
        pill.className = 'step-pill';
        pill.innerText = slide.date;
        pill.onclick = () => updateSlide(idx);
        container.appendChild(pill);
    }});
}}

function buildDownloadGrid() {{
    const grid = document.getElementById('downloadGrid');
    grid.innerHTML = '';
    slides.forEach((slide) => {{
        const div = document.createElement('div');
        div.className = 'download-item';
        div.innerHTML = `
            <span><strong>${{slide.date}}</strong> (${{slide.items.length}} dalle(s))</span>
            <button class="btn" style="padding: 6px 12px; font-size: 11px;" onclick="downloadZipForDate('${{slide.iso}}')">ZIP Date</button>
        `;
        grid.appendChild(div);
    }});
}}

async function downloadZipForDate(isoDate) {{
    const slide = slides.find(s => s.iso === isoDate);
    if (!slide) return;

    const status = document.getElementById('statusMsg');
    status.innerText = `Préparation du ZIP pour le ${{slide.date}}...`;

    const zip = new JSZip();
    const folder = zip.folder(`Sentinel_${{isoDate}}`);

    for (let i = 0; i < slide.items.length; i++) {{
        const item = slide.items[i];
        if (item.downloadUrl) {{
            try {{
                status.innerText = `Téléchargement de la dalle ${{i + 1}} / ${{slide.items.length}} (${{slide.date}})...`;
                const response = await fetch(item.downloadUrl);
                const blob = await response.blob();
                folder.file(`dalle_${{i + 1}}_${{item.itemId}}.tif`, blob);
            }} catch (e) {{
                console.error("Erreur téléchargement dalle", e);
            }}
        }}
    }}

    status.innerText = `Compression et génération du ZIP pour le ${{slide.date}}...`;
    const content = await zip.generateAsync({{ type: "blob" }});
    saveAs(content, `Sentinel_${{isoDate}}.zip`);
    status.innerText = `Téléchargement du ZIP pour le ${{slide.date}} terminé !`;
    setTimeout(() => {{ status.innerText = ""; }}, 4000);
}}

async function downloadEverythingZip() {{
    const status = document.getElementById('statusMsg');
    for (let slide of slides) {{
        await downloadZipForDate(slide.iso);
    }}
    status.innerText = "Tous les packages ZIP ont été générés avec succès !";
    setTimeout(() => {{ status.innerText = ""; }}, 5000);
}}

if (slides.length > 0) {{
    buildStepsContainer();
    updateSlide(0);
    buildDownloadGrid();
}}
</script>
</body>
</html>
"""
            out_path = os.path.join(out_dir, "rapport_sentinel_mosaique.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            webbrowser.open('file://' + os.path.abspath(out_path))
            QMessageBox.information(self, "Succès", f"Rapport HTML interactif généré et ouvert avec succès :\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class SentinelPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "Sentinel-2 Timelapse", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Sentinel Export", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Sentinel Export", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not self.dialog:
            self.dialog = SentinelExportDialog(self.iface.mainWindow())
        self.dialog.show()