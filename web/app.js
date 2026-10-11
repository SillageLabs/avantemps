"use strict";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const labels = {
  warm_index: "Indice en zone positive (signal chaud)",
  cold_index: "Indice en zone négative (signal froid)",
  neutral_index: "Indice proche de la zone neutre"
};
function element(tag, attrs = {}, text = "") {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  if (text) node.textContent = text;
  return node;
}
function draw(records) {
  const svg = $("chart");
  svg.replaceChildren();
  if (!records.length) return;
  const values = records.map(r => Number(r.anomaly_c));
  const range = Math.max(1, ...values.map(v => Math.abs(v)), 0.5) + 0.2;
  const left = 55, top = 18, width = 635, height = 214;
  const x = i => left + (i / Math.max(1, records.length - 1)) * width;
  const y = v => top + ((range - v) / (range * 2)) * height;
  [-range, -0.5, 0, 0.5, range].forEach(value => {
    const dashed = value === 0 ? "chart-zero" : (Math.abs(value) === 0.5 ? "chart-threshold" : "chart-grid");
    svg.append(element("line", {x1: left, x2: left + width, y1: y(value), y2: y(value), class: dashed}));
    svg.append(element("text", {x: left - 9, y: y(value) + 4, "text-anchor": "end", class: "axis-label"}, value.toFixed(1)));
  });
  const points = values.map((v, i) => x(i).toFixed(1) + "," + y(v).toFixed(1)).join(" ");
  svg.append(element("polyline", {points, class: "chart-line"}));
  svg.append(element("circle", {cx: x(values.length - 1), cy: y(values[values.length - 1]), r: 5, class: "chart-point"}));
  const last = records[records.length - 1];
  const first = records[0];
  svg.append(element("text", {x: left, y: 265, class: "axis-label"}, first.season + " " + first.year));
  svg.append(element("text", {x: left + width, y: 265, "text-anchor": "end", class: "axis-label"}, last.season + " " + last.year));
  $("chart-fallback").textContent = "Valeurs observées RONI (°C). Les seuils pointillés ne sont pas des alertes.";
}
async function getJSON(route) {
  const response = await fetch(route, {cache: "no-store"});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Service indisponible");
  return data;
}
async function refresh() {
  $("loading").hidden = false;
  $("loading").textContent = "Chargement des données locales…";
  $("observation").hidden = true;
  try {
    const [current, history, archive] = await Promise.all([
      getJSON("/api/roni/latest"),
      getJSON("/api/roni/history?limit=36"),
      getJSON("/api/roni/versions")
    ]);
    const latest = current.summary.latest;
    $("index-value").textContent = Number(latest.anomaly_c).toLocaleString("fr-FR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
    $("season-label").textContent = "Saison glissante " + latest.season + " " + latest.year + " — observation";
    $("signal-label").textContent = labels[current.summary.signal] || "Signal non déterminé";
    const delta = current.summary.delta_from_previous_c;
    $("comparison").textContent = delta === null ? "Aucune valeur antérieure." : "Écart avec la saison précédente : " + (delta > 0 ? "+" : "") + Number(delta).toLocaleString("fr-FR") + " °C.";
    $("collected").textContent = new Date(current.retrieved_at_utc).toLocaleString("fr-FR", {dateStyle: "medium", timeStyle: "short", timeZone: "UTC"}) + " UTC (date de récupération)";
    $("digest").textContent = current.id.slice(0, 16) + "…";
    $("versions").textContent = String(archive.versions.length);
    draw(history.records);
    $("loading").hidden = true;
    $("observation").hidden = false;
  } catch (error) {
    $("loading").hidden = false;
    $("loading").textContent = "Données indisponibles : " + error.message + " Aucun chiffre n'est simulé.";
    $("chart").replaceChildren();
    $("chart-fallback").textContent = "Aucune courbe à afficher.";
    $("collected").textContent = "—";
    $("digest").textContent = "—";
    $("versions").textContent = "—";
  }
}
$("refresh").addEventListener("click", refresh);
refresh();
