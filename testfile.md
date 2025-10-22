{% extends "master.html" %}

{% block title %}
  Analyse: {{ data_file.title }}
{% endblock %}

{% block extra_head %}
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer/dist/css/material.css" />

    <style>
        /* Maximale Größe für den Analysebereich nutzen */
        #main-container {
            max-width: 98%;
            [span_0](start_span)padding-bottom: 10px;[span_0](end_span)
        }

        /* Styling für den Perspective Viewer Container */
        #perspective-container {
            /* Höhe festlegen, damit Perspective den Platz füllt (wichtig!) */
            height: 80vh;
            [span_1](start_span)min-height: 600px;[span_1](end_span)
            margin-top: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid var(--dws-lightgrey);
            position: relative;
            [span_2](start_span)/* Für das Loader-Overlay */[span_2](end_span)
        }

        perspective-viewer {
            width: 100%;
            [span_3](start_span)height: 100%;[span_3](end_span)
        }

        /* Lade-Overlay Styling */
        #loader {
            display: flex;
            [span_4](start_span)align-items: center;[span_4](end_span)
            justify-content: center;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            [span_5](start_span)z-index: 100;[span_5](end_span)
            font-size: 1.1em;
            color: var(--dws-grey);
            text-align: center;
            [span_6](start_span)padding: 20px;[span_6](end_span)
        }

        /* --- Excel Sheet Selector --- */
        .analysis-controls {
            display: flex;
            [span_7](start_span)justify-content: flex-end;[span_7](end_span)
            align-items: center;
            margin-bottom: 5px;
        }
        .sheet-selector {
            display: flex;
            [span_8](start_span)align-items: center;[span_8](end_span)
            gap: 10px;
        }
        .sheet-selector label {
            font-weight: bold;
            [span_9](start_span)margin-bottom: 0;[span_9](end_span)
        }
        .sheet-selector select {
            width: auto;
            [span_10](start_span)min-width: 200px;[span_10](end_span)
            padding: 10px;
        }
    </style>

    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective/dist/umd/perspective.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer/dist/umd/perspective-viewer.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-datagrid/dist/umd/perspective-viewer-datagrid.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-d3fc/dist/umd/perspective-viewer-d3fc.js"></script>
{% endblock %}

{% block content %}
  <h1>Datenanalyse: {{ data_file.title }}</h1>
  <p>
    <a href="{% url 'dashboard' %}">&larr; [span_11](start_span)Zurück zum Dashboard</a> |[span_11](end_span)
    <a href="{% url 'datafiles:download' data_file.id %}">Originaldatei herunterladen</a>
  </p>

  {% if sheet_names|length > 1 %}
  <div class="analysis-controls">
      <div class="sheet-selector">
          <label for="sheet-select">Excel Arbeitsblatt:</label>
          <select id="sheet-select">
              {% for sheet in sheet_names %}
              <option value="{{ sheet }}" {% if sheet == selected_sheet %}selected{% endif %}>
                  [span_12](start_span){{ sheet }}[span_12](end_span)
              </option>
              {% endfor %}
          </select>
      </div>
  </div>
  {% endif %}

  <div id="perspective-container">
    <div id="loader"><span>⏳ Lade und analysiere Daten...<br><small>(Die Daten werden optimiert übertragen. Dies kann bei großen Dateien einen Moment dauern.)</small></span></div>
    <perspective-viewer id="viewer"></perspective-viewer>
  </div>

 
  [span_13](start_span)<script defer>[span_13](end_span)

        // Sheet-Wechsel
        document.getElementById('sheet-select')?.addEventListener("change", (event) => {
          window.location.href = "?sheet=" + encodeURIComponent(event.target.value);
        [span_14](start_span)});[span_14](end_span)

        [span_15](start_span)async function loadData() {[span_15](end_span)
            const viewer = document.getElementById("viewer");
            const loader = document.getElementById("loader");
            [span_16](start_span)try {[span_16](end_span)
                // 1. URL für den Datenabruf konstruieren (?format=arrow).
                [span_17](start_span)let dataUrl = "{% url 'datafiles:analyze' data_file.id %}?format=arrow";[span_17](end_span)

                [span_18](start_span)const selectedSheet = "{{ selected_sheet|escapejs }}";[span_18](end_span)
                [span_19](start_span)// WICHTIG: Prüfen, ob der Wert gültig UND nicht der String "None" ist (Django Template Verhalten).[span_19](end_span)
                [span_20](start_span)if (selectedSheet && selectedSheet !== 'None') {[span_20](end_span)
                    dataUrl += "&sheet=" + encodeURIComponent(selectedSheet);
                [span_21](start_span)}

                // 2. Daten vom Server abrufen (Streaming)
                const response = await fetch(dataUrl);
                if (!response.ok) {[span_21](end_span)
                    // Fehlerbehandlung, wenn der Server (z.B. views.py) einen Fehler meldet (Status 500/404)
                    const errorText = await response.text();
                    [span_22](start_span)throw new Error(`Server-Fehler (Status ${response.status}): ${errorText}`);[span_22](end_span)
                }

                // 3. Antwort als ArrayBuffer lesen (Binärdaten/Arrow Stream)
                const buffer = await response.arrayBuffer();
                [span_23](start_span)if (buffer.byteLength === 0) {[span_23](end_span)
                    loader.textContent = "Die Datei oder das ausgewählte Sheet ist leer.";
                    [span_24](start_span)return;[span_24](end_span)
                }

                // 4. Daten in Perspective laden (via Worker)
                // Der Worker verarbeitet den Arrow-Buffer effizient in WebAssembly.
                // 'perspective' ist jetzt global verfügbar (durch die UMD-Skripte im <head>)
                [span_25](start_span)const table = await perspective.table(buffer);[span_25](end_span)

                // 5. Tabelle an den Viewer binden
                await viewer.load(table);
                [span_26](start_span)// 6. Standardkonfiguration des Viewers (Excel-ähnliche Pivot-Funktionalität ist standardmäßig verfügbar)[span_26](end_span)
                await viewer.restore({
                    [span_27](start_span)plugin: "Datagrid", // Standardansicht ist die Tabelle[span_27](end_span)
                    [span_28](start_span)settings: true,     // Zeigt das Konfigurationsmenü (Sidebar) an[span_28](end_span)
                    theme: "Material Light"
                [span_29](start_span)});[span_29](end_span)

                // 7. Lade-Overlay entfernen
                loader.style.display = "none";
            [span_30](start_span)} catch (error) {[span_30](end_span)
                console.error("Fehler während der Datenanalyse:", error);
                [span_31](start_span)loader.innerHTML = `<span style="color: red;">Kritischer Fehler beim Laden oder Verarbeiten der Daten.<br><small>${error.message}</small></span>`;[span_31](end_span)
            [span_32](start_span)}
        }

        // Startet den Ladevorgang.
        // Da dies ein Modul ist (type="module"), wird es automatisch[span_32](end_span)
        // nach dem Parsen des DOM ausgeführt (deferred).
        [span_33](start_span)loadData();[span_33](end_span)
  </script>
{% endblock %}
