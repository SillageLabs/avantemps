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

function showChanges(payload) {
  const status = $("revision-status");
  const list = $("revision-list");
  list.replaceChildren();
  if (payload.status === "insufficient_versions") {
    status.textContent = "Une seule version archivée : les révisions pourront être comparées après une prochaine modification du fichier source.";
    return;
  }
  const result = payload.comparison;
  const c = result.counts;
  status.textContent = [
    c.revised + " saison(s) corrigée(s)",
    c.added + " ajoutée(s)",
    c.removed + " retirée(s)"
  ].join(" · ") + " entre deux versions du fichier NOAA.";
  if (!result.changes.length) {
    const item = document.createElement("li");
    item.textContent = "Le fichier a changé, mais aucune valeur chiffrée n'a été modifiée.";
    list.append(item);
    return;
  }
  // Les plus récentes en premier. On indique uniquement les changements entre ARCHIVES.
  result.changes.slice(-12).reverse().forEach(entry => {
    const item = document.createElement("li");
    const label = entry.season + " " + entry.year + " : ";
    if (entry.type === "revised") {
      item.textContent = label + "révision de " + entry.old_anomaly_c +
        " à " + entry.new_anomaly_c + " °C (" +
        (entry.delta_c > 0 ? "+" : "") + entry.delta_c + " °C).";
    } else if (entry.type === "added") {
      item.textContent = label + "nouvelle observation : " + entry.new_anomaly_c + " °C.";
    } else {
      item.textContent = label + "observation absente de la nouvelle version.";
    }
    list.append(item);
  });
  if (result.changes.length > 12) {
    const item = document.createElement("li");
    item.textContent = (result.changes.length - 12) + " autre(s) changement(s) disponible(s) via l'API.";
    list.append(item);
  }
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
    $("freshness-status").textContent = current.freshness?.message ||
      "Fraîcheur indéterminée : consulter les dates et la source officielle.";
    $("index-value").textContent = Number(latest.anomaly_c).toLocaleString("fr-FR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
    $("season-label").textContent = "Saison glissante " + latest.season + " " + latest.year + " — observation";
    $("signal-label").textContent = labels[current.summary.signal] || "Signal non déterminé";
    const delta = current.summary.delta_from_previous_c;
    $("comparison").textContent = delta === null ? "Aucune valeur antérieure." : "Écart avec la saison précédente : " + (delta > 0 ? "+" : "") + Number(delta).toLocaleString("fr-FR") + " °C.";
    const asUTC = value => new Date(value).toLocaleString("fr-FR", {dateStyle: "medium", timeStyle: "short", timeZone: "UTC"}) + " UTC";
    $("collected").textContent = asUTC(current.last_checked_at_utc || current.retrieved_at_utc);
    $("first-collected").textContent = asUTC(current.retrieved_at_utc);
    $("digest").textContent = current.id.slice(0, 16) + "…";
    $("versions").textContent = String(archive.versions.length);
    draw(history.records);
    $("loading").hidden = true;
    $("observation").hidden = false;
    try {
      showChanges(await getJSON("/api/roni/changes"));
    } catch (error) {
      $("revision-status").textContent = "Comparaison indisponible : " + error.message;
      $("revision-list").replaceChildren();
    }
  } catch (error) {
    $("loading").hidden = false;
    $("freshness-status").textContent = "Fraîcheur indéterminée : archive indisponible.";
    $("loading").textContent = "Données indisponibles : " + error.message + " Aucun chiffre n'est simulé.";
    $("chart").replaceChildren();
    $("chart-fallback").textContent = "Aucune courbe à afficher.";
    $("collected").textContent = "—";
    $("first-collected").textContent = "—";
    $("revision-status").textContent = "Comparaison indisponible sans archive valide.";
    $("revision-list").replaceChildren();
    $("digest").textContent = "—";
    $("versions").textContent = "—";
  }
}
$("refresh").addEventListener("click", refresh);
refresh();


function safeOfficialLink(address) {
  try {
    const url = new URL(address);
    if (url.protocol !== "https:" || !["meteo.nc", "meteofrance.com", "meteofrance.gf"].includes(url.hostname)) {
      return null;
    }
    return url.href;
  } catch (_) {
    return null;
  }
}

function addEvidence(target, claim, sources) {
  const article = document.createElement("article");
  article.className = "evidence-item";
  const kind = document.createElement("p");
  kind.className = "evidence-kind";
  kind.textContent = ({
    documented_association: "CLIMATOLOGIE · TENDANCE HISTORIQUE",
    dated_official_bulletin: "BULLETIN OFFICIEL · DATÉ",
    dated_observation: "OBSERVATION MESURÉE · DATÉE"
  })[claim.kind] || "INFORMATION";
  const heading = document.createElement("h5");
  heading.textContent = claim.subject;
  const description = document.createElement("p");
  description.textContent = claim.detail;
  article.append(kind, heading, description);
  if (claim.scope || claim.reference_period) {
    const scope = document.createElement("p");
    scope.className = "muted small";
    scope.textContent = "Périmètre : " + (claim.scope || claim.reference_period);
    article.append(scope);
  }
  const references = document.createElement("div");
  references.className = "evidence-references";
  for (const sourceId of claim.source_ids) {
    const source = sources[sourceId];
    if (!source) continue;
    const safe = safeOfficialLink(source.url);
    if (!safe) continue;
    const link = document.createElement("a");
    link.href = safe;
    link.rel = "noopener noreferrer";
    link.target = "_blank";
    link.textContent = source.publisher + " · " + source.published_on + " ↗";
    references.append(link);
  }
  article.append(references);
  target.append(article);
}

function renderTerritory(profile) {
  $("territory-name").textContent = profile.name;
  $("territory-intro").textContent = profile.intro;
  $("territory-conclusion").textContent = profile.conclusion;
  $("territory-disclaimer").textContent = profile.disclaimer;
  $("territory-review").textContent = "Dossier revu le " +
    new Date(profile.reviewed_on + "T12:00:00Z").toLocaleDateString("fr-FR", {dateStyle: "long", timeZone: "UTC"}) +
    " · Documentation figée, non actualisée automatiquement.";
  const evaluated = profile.status === "documented_climatology";
  $("territory-status").textContent = evaluated ?
    "Tendances historiques sourcées — aucune prévision locale générée" :
    "Non évalué — AVANTEMPS ne formule aucune conclusion";
  for (const [elementId, facts, absence] of [
    ["territory-climatology", profile.climatology, "Aucune relation territoriale vérifiée dans AVANTEMPS."],
    ["territory-publications", profile.dated_publications, "Aucune publication locale intégrée pour ce territoire."]
  ]) {
    const target = $(elementId);
    target.replaceChildren();
    if (facts.length === 0) {
      const message = document.createElement("p");
      message.className = "muted";
      message.textContent = absence;
      target.append(message);
    } else {
      facts.forEach(claim => addEvidence(target, claim, profile.sources));
    }
  }
  const official = safeOfficialLink(profile.official_information_url);
  $("territory-official").hidden = !official;
  if (official) $("territory-official").href = official;
  $("territory-content").hidden = false;
}

async function loadTerritory() {
  const selected = $("territory-choice").value;
  $("territory-loading").hidden = false;
  $("territory-loading").textContent = "Ouverture du dossier documentaire…";
  $("territory-content").hidden = true;
  try {
    if (!/^[a-z-]+$/.test(selected)) throw Error("Identifiant incorrect");
    const profile = await getJSON("/api/territories/" + selected);
    if ($("territory-choice").value !== selected) return;
    renderTerritory(profile);
    $("territory-loading").hidden = true;
  } catch (error) {
    $("territory-loading").textContent = "Dossier indisponible : " + error.message;
  }
}

async function setupTerritories() {
  try {
    const data = await getJSON("/api/territories");
    const select = $("territory-choice");
    select.replaceChildren();
    for (const item of data.territories) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.name + (item.status === "not_assessed" ? " · non évalué" : "");
      select.append(option);
    }
    if (data.territories.some(item => item.id === "nouvelle-caledonie")) {
      select.value = "nouvelle-caledonie";
    }
    if (!select.value) throw Error("Aucun territoire renseigné");
    select.addEventListener("change", loadTerritory);
    await loadTerritory();
  } catch (error) {
    $("territory-loading").textContent = "Impossible de charger les territoires : " + error.message;
  }
}

setupTerritories();


async function refreshVerificationStatus() {
  const el = $("verification-status");
  try {
    const report = await getJSON("/api/verification/status");
    if (report.status !== "not_evaluated" || report.publication_authorized !== false) {
      throw Error("Réponse scientifique inattendue");
    }
    el.textContent = "Qualité prédictive : non évaluée. Aucune preuve de performance territoriale disponible.";
  } catch (_) {
    el.textContent = "Statut de vérification indisponible : aucune prévision n'est affichée.";
  }
}
refreshVerificationStatus();
