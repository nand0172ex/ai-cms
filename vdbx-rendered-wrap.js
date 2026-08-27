<script>
(function(){
const shell = document.getElementById("vdbx-shell");
if (!shell) return;

const tabs = shell.querySelectorAll(".vdbx-tab");
const sections = shell.querySelectorAll(".vdbx-section");

function badgeClass(status) {
const s = String(status || "").toLowerCase();
if (s.includes("success") || s.includes("connected") || s.includes("green")) return "vdbx-green";
if (s.includes("failed") || s.includes("error") || s.includes("red") || s.includes("disconnect")) return "vdbx-red";
if (s.includes("running") || s.includes("pending") || s.includes("amber") || s.includes("warn")) return "vdbx-amber";
return "vdbx-gray";
}

async function api(url, options) {
    const requestOptions = options || {};
    requestOptions.headers = Object.assign({}, requestOptions.headers || {});
    const csrfCookie = document.cookie.split('; ').find((item) => item.indexOf('csrftoken=') === 0);
    if (csrfCookie) {
        requestOptions.headers['X-CSRFToken'] = decodeURIComponent(csrfCookie.split('=')[1]);
    }
    const res = await fetch(url, requestOptions);
let payload = {};
try { payload = await res.json(); } catch (_e) { payload = {}; }
if (!res.ok) throw new Error(payload.error || payload.detail || ("Request failed: " + res.status));
return payload;
}

function bindEvent(id, eventName, handler) {
const el = document.getElementById(id);
if (el) el.addEventListener(eventName, handler);
return el;
}

function setActive(target) {
tabs.forEach((tab) => tab.classList.toggle("active", tab.getAttribute("data-target") === target));
sections.forEach((sec) => sec.classList.toggle("active", sec.getAttribute("data-section") === target));
}

tabs.forEach((tab) => {
tab.addEventListener("click", (event) => {
    event.preventDefault();
    const target = tab.getAttribute("data-target");
    setActive(target);
});
});

shell.querySelectorAll("[data-quick]").forEach((button) => {
button.addEventListener("click", () => {
    const target = button.getAttribute("data-quick");
    if (target === "create") createCollectionFlow();
    else setActive(target);
});
});

async function loadDashboard() {
const kpiEl = document.getElementById("vdbx-kpis");
const actEl = document.getElementById("vdbx-activities");
try {
    const data = await api("/api/v1/vector-db/dashboard/");
    const d = data.dashboard || {};
    const status = String(d.qdrant_status || "unknown");
    const kpiDefs = [
        {k:"Collections", v:d.total_collections || 0, sub:"Total Collections", icon:"&#9638;", color:"#2f6fed"},
        {k:"Vectors", v:d.total_vectors || 0, sub:"Total Vectors", icon:"&#9670;", color:"#7c3aed"},
        {k:"Documents", v:d.total_documents || 0, sub:"Total Documents", icon:"&#9636;", color:"#0891b2"},
        {k:"Chunks", v:d.total_chunks || 0, sub:"Indexed Chunks", icon:"&#9642;", color:"#d97706"},
        {k:"Storage", v:"Live", sub:"Qdrant Storage", icon:"&#9679;", color:"#059669"},
        {k:"Status", v:status, sub:"Connection Health", icon:"&#9889;", color: status === "connected" ? "#16a34a" : "#dc2626", badge:true}
    ];
    kpiEl.innerHTML = kpiDefs.map((x) =>
        '<div class="vdbx-kpi-card">' +
            '<div class="vdbx-kpi-icon" style="background:' + x.color + '1a; color:' + x.color + ';">' + x.icon + '</div>' +
            '<div class="vdbx-kpi-info">' +
                '<div class="vdbx-kpi-label">' + x.k + '</div>' +
                (x.badge ? '<span class="vdbx-badge ' + badgeClass(x.v) + '">' + x.v + '</span>' : '<div class="vdbx-kpi-value">' + x.v + '</div>') +
                '<div class="vdbx-kpi-sub">' + x.sub + '</div>' +
            '</div>' +
        '</div>'
    ).join("");

    const acts = d.recent_activities || [];
    if (!acts.length) {
        actEl.innerHTML = '<span class="vdbx-tip">No recent activities.</span>';
    } else {
        actEl.innerHTML = '<ul class="vdbx-list">' + acts.slice(0, 20).map((a) =>
            '<li><strong>' + (a.label || '-') + '</strong> <span class="vdbx-badge ' + badgeClass(a.status) + '">' + (a.status || 'info') + '</span> ' +
            '<span class="vdbx-tip">' + (a.timestamp || '') + '</span></li>'
        ).join('') + '</ul>';
    }
} catch (err) {
    kpiEl.innerHTML = '<div class="vdbx-card"><div class="body"><span class="vdbx-badge vdbx-red">Error</span> ' + err.message + '</div></div>';
    actEl.textContent = 'Unable to load activities: ' + err.message;
}
}

async function loadCollections() {
const table = document.getElementById("vdbx-collections-table");
try {
    const data = await api("/api/v1/vector-db/collections/");
    const rows = data.results || [];
    if (!rows.length) {
        table.innerHTML = '<span class="vdbx-tip">No collections found on the currently connected Qdrant host.</span>';
        return;
    }
    table.innerHTML = '<table class="vdbx-table"><thead><tr>' +
        '<th>Collection</th><th>Health</th><th>Vectors</th><th>Docs</th><th>Dimension</th><th>Actions</th>' +
        '</tr></thead><tbody>' +
        rows.map((r) =>
            (function() {
            const slug = r.knowledge_base_slug || "";
            const actions = slug
                ? ('<button class="vdbx-btn" data-action="stats" data-slug="' + slug + '">Stats</button> ' +
                   '<button class="vdbx-btn" data-action="edit" data-slug="' + slug + '">Edit</button> ' +
                   '<button class="vdbx-btn" data-action="delete" data-slug="' + slug + '">Delete</button>')
                : '<span class="vdbx-tip">Live collection only</span>';
            return (
            '<tr>' +
            '<td><strong>' + (r.collection || '-') + '</strong><br><span class="vdbx-tip">KB: ' + (r.knowledge_base_slug || '-') + '</span></td>' +
            '<td><span class="vdbx-badge ' + badgeClass(r.health) + '">' + (r.health || 'unknown') + '</span></td>' +
            '<td>' + (r.vectors_count || 0) + '</td>' +
            '<td>' + (r.points_count || 0) + '</td>' +
            '<td>' + (r.vector_size || '-') + '</td>' +
            '<td>' + actions + '</td>' +
            '</tr>'
            );
            })()
        ).join('') + '</tbody></table>';
    const overview = document.getElementById("vdbx-collections-overview");
    if (overview) overview.innerHTML = table.innerHTML;
} catch (err) {
    table.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

const modalOverlay = document.getElementById("vdbx-collection-modal");
const modalTitle = document.getElementById("vdbx-modal-title");
const modalName = document.getElementById("vdbx-modal-name");
const modalKey = document.getElementById("vdbx-modal-key");
const modalDimension = document.getElementById("vdbx-modal-dimension");
const modalThreshold = document.getElementById("vdbx-modal-threshold");
const modalTopK = document.getElementById("vdbx-modal-topk");
const modalError = document.getElementById("vdbx-modal-error");
const modalSubmit = document.getElementById("vdbx-modal-submit");
let modalMode = "create";
let modalSlug = null;

function openModal(mode, prefill) {
    modalMode = mode;
    modalSlug = (prefill && prefill.slug) || null;
    modalError.textContent = "";
    modalTitle.textContent = mode === "edit" ? "Edit Collection" : "Create Collection";
    modalSubmit.textContent = mode === "edit" ? "Save Changes" : "Create Collection";
    modalName.value = (prefill && prefill.name) || "";
    modalKey.value = (prefill && prefill.collection_name) || "";
    modalKey.disabled = mode === "edit";
    modalDimension.value = (prefill && prefill.vector_size) || "1536";
    modalDimension.disabled = mode === "edit";
    modalThreshold.value = (prefill && prefill.similarity_threshold) || "0.7";
    modalTopK.value = (prefill && prefill.top_k) || "5";
    modalOverlay.classList.add("open");
    modalName.focus();
}

function closeModal() {
    modalOverlay.classList.remove("open");
}

async function submitModal() {
    const name = modalName.value.trim();
    if (!name) {
        modalError.textContent = "Collection name is required.";
        return;
    }
    modalError.textContent = "";
    modalSubmit.disabled = true;
    modalSubmit.textContent = "Saving...";
    try {
        if (modalMode === "create") {
            await api("/api/v1/vector-db/collections/", {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    name,
                    collection_name: modalKey.value.trim(),
                    vector_size: Number(modalDimension.value || "1536"),
                    similarity_threshold: Number(modalThreshold.value || "0.7"),
                    top_k: Number(modalTopK.value || "5"),
                }),
            });
        } else {
            await api("/api/v1/vector-db/collections/" + modalSlug + "/", {
                method: "PATCH",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    name,
                    top_k: Number(modalTopK.value || "5"),
                    similarity_threshold: Number(modalThreshold.value || "0.7"),
                }),
            });
        }
        closeModal();
        await Promise.all([loadDashboard(), loadCollections()]);
    } catch (err) {
        modalError.textContent = err.message;
    } finally {
        modalSubmit.disabled = false;
        modalSubmit.textContent = modalMode === "edit" ? "Save Changes" : "Create Collection";
    }
}

function createCollectionFlow() {
    openModal("create", null);
}

bindEvent("vdbx-modal-close", "click", closeModal);
bindEvent("vdbx-modal-cancel", "click", closeModal);
bindEvent("vdbx-modal-submit", "click", submitModal);
if (modalOverlay) modalOverlay.addEventListener("click", (event) => { if (event.target === modalOverlay) closeModal(); });

async function collectionAction(action, slug) {
if (!slug) return;
try {
    if (action === "stats") {
        const data = await api("/api/v1/vector-db/collections/" + slug + "/");
        window.alert("Collection: " + data.collection + "\nPoints: " + ((data.stats || {}).points_count || 0) + "\nVectors: " + ((data.stats || {}).vectors_count || 0));
        return;
    }
    if (action === "edit") {
        const data = await api("/api/v1/vector-db/collections/" + slug + "/");
        openModal("edit", {
            slug,
            name: data.name,
            collection_name: data.collection,
            vector_size: data.vector_size,
            top_k: data.top_k,
            similarity_threshold: data.similarity_threshold,
        });
        return;
    }
    if (action === "delete") {
        if (!window.confirm("Delete collection and knowledge base " + slug + "?")) return;
        await api("/api/v1/vector-db/collections/" + slug + "/", { method: "DELETE" });
    }
    await Promise.all([loadDashboard(), loadCollections()]);
} catch (err) {
    window.alert(action + " failed: " + err.message);
}
}

async function loadUploads() {
const jobsEl = document.getElementById("vdbx-upload-jobs");
try {
    const data = await api("/api/v1/vector-db/uploads/status/");
    const rows = data.results || [];
    const qdrant = data.qdrant || {};
    const qdrantClass = qdrant.status === "connected" ? "vdbx-green" : "vdbx-red";
    const qdrantLabel = qdrant.status === "connected" ? "Qdrant connected" : "Qdrant unavailable";
    const qdrantDetail = qdrant.status === "connected"
        ? "Live connection to " + (qdrant.url || "configured host") + (qdrant.latency_ms ? " (" + qdrant.latency_ms + "ms)" : "")
        : (qdrant.error || "The configured Qdrant host could not be reached.");
    const header = '<div style="display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:12px; flex-wrap:wrap;">' +
        '<span class="vdbx-badge ' + qdrantClass + '">' + qdrantLabel + '</span>' +
        '<span class="vdbx-tip">' + qdrantDetail + '</span></div>';
    if (!rows.length) {
        jobsEl.innerHTML = header + '<span class="vdbx-tip">No upload jobs found.</span>';
        return;
    }
    jobsEl.innerHTML = header + '<table class="vdbx-table"><thead><tr><th>Document</th><th>Ingestion</th><th>Qdrant</th><th>Collection</th><th>Chunks</th><th>Details</th></tr></thead><tbody>' +
        rows.map((r) => '<tr><td>' + (r.document || '-') + '<br><span class="vdbx-tip">' + (r.knowledge_base || '-') + '</span></td>' +
            '<td><span class="vdbx-badge ' + badgeClass(r.status) + '">' + (r.status || '-') + '</span></td>' +
            '<td><span class="vdbx-badge ' + (r.qdrant_status === "connected" ? "vdbx-green" : "vdbx-red") + '">' + (r.qdrant_status || "unknown") + '</span></td>' +
            '<td><span class="vdbx-badge ' + (r.collection_status === "available" ? "vdbx-green" : r.collection_status === "missing" ? "vdbx-amber" : "vdbx-red") + '">' + (r.collection_status || "unknown") + '</span></td>' +
            '<td>' + (r.chunk_count || 0) + '</td><td class="vdbx-tip">' + (r.status_detail || r.error_message || '-') + '</td></tr>').join('') +
        '</tbody></table>';
} catch (err) {
    jobsEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

function bindUpload() {
const zone = document.getElementById("vdbx-dropzone");
const input = document.getElementById("vdbx-file-input");
const titleEl = document.getElementById("vdbx-upload-title");
const kbEl = document.getElementById("vdbx-upload-kb");
const embeddingEl = document.getElementById("vdbx-upload-embedding");
const status = document.getElementById("vdbx-upload-status");
const progress = document.getElementById("vdbx-upload-progress");

function send(file) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    if (titleEl.value.trim()) form.append("title", titleEl.value.trim());
    if (kbEl.value.trim()) form.append("knowledge_base_slug", kbEl.value.trim());
    if (embeddingEl && embeddingEl.value.trim()) form.append("embedding_profile_slug", embeddingEl.value.trim());

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/v1/upload-file/");
            const csrfCookie = document.cookie.split('; ').find((item) => item.indexOf('csrftoken=') === 0);
            if (csrfCookie) {
                xhr.setRequestHeader("X-CSRFToken", decodeURIComponent(csrfCookie.split('=')[1]));
            }
    xhr.upload.onprogress = function(e) {
        if (!e.lengthComputable) return;
        const pct = Math.max(2, Math.floor((e.loaded / e.total) * 100));
        progress.style.width = pct + "%";
    };
    xhr.onload = async function() {
        try {
            const payload = JSON.parse(xhr.responseText || "{}");
            if (xhr.status >= 200 && xhr.status < 300) {
                status.textContent = "Upload complete. Job " + payload.job_id + ", chunks " + (payload.chunk_count || 0) + ".";
                status.style.color = "#17663b";
                await Promise.all([loadDashboard(), loadUploads()]);
            } else {
                status.textContent = payload.error || "Upload failed";
                status.style.color = "#8b1e24";
            }
        } catch (_e) {
            status.textContent = "Upload failed.";
            status.style.color = "#8b1e24";
        }
    };
    xhr.onerror = function() {
        status.textContent = "Upload failed due to network issue.";
        status.style.color = "#8b1e24";
    };

    progress.style.width = "4%";
    status.textContent = "Uploading and indexing...";
    status.style.color = "#224774";
    xhr.send(form);
}

zone.addEventListener("click", () => input.click());
input.addEventListener("change", () => send(input.files && input.files[0]));
zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.style.background = "#eef5ff"; });
zone.addEventListener("dragleave", () => { zone.style.background = "#f8fbff"; });
zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.style.background = "#f8fbff";
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    send(file);
});
}

async function loadSync() {
const conn = document.getElementById("vdbx-sync-connectors");
const hist = document.getElementById("vdbx-sync-history");
const statusEl = document.getElementById("vdbx-connector-status");
try {
    const [registryData, syncData] = await Promise.all([
        api("/api/v1/vector-db/connectors/"),
        api("/api/v1/vector-db/sync/status/"),
    ]);
    const connectors = registryData.results || [];
    const history = syncData.sync_history || [];

    if (!connectors.length) {
        conn.innerHTML = '<span class="vdbx-tip">No sources configured yet. Add your first source above.</span>';
    } else {
        conn.innerHTML = '<table class="vdbx-table"><thead><tr><th>Source</th><th>Type</th><th>Embedding</th><th>Schedule</th><th>Records</th><th>Last Sync</th><th>Actions</th></tr></thead><tbody>' +
            connectors.map((c) => '<tr>' +
                '<td><strong>' + c.name + '</strong><br><span class="vdbx-tip">' + (c.knowledge_base_slug || '-') + '</span></td>' +
                '<td>' + c.connector_type + '</td>' +
            '<td>' + (c.embedding_profile_name || c.embedding_profile_slug || 'default') + '</td>' +
            '<td>' + ((Number(c.sync_interval_minutes || 30) >= 1440) ? '24h' : '30m') + '<br><span class="vdbx-tip">' + (c.sync_mode || 'incremental') + '</span></td>' +
                '<td>' + (c.record_count || 0) + '</td>' +
                '<td><span class="vdbx-badge ' + badgeClass(c.last_sync_status || 'gray') + '">' + (c.last_sync_status || 'unknown') + '</span><br><span class="vdbx-tip">' + (c.last_sync_time || '-') + '</span></td>' +
                '<td>' +
                    '<button class="vdbx-btn" data-edit-connector="' + c.id + '">Edit</button> ' +
                    '<button class="vdbx-btn" data-test-connector="' + c.id + '">Test</button> ' +
                    '<button class="vdbx-btn" data-sync-connector="' + c.id + '">Sync</button> ' +
                    '<button class="vdbx-btn" data-delete-connector="' + c.id + '">Delete</button>' +
                '</td>' +
            '</tr>').join('') + '</tbody></table>';
    }

    if (!history.length) {
        hist.innerHTML = '<span class="vdbx-tip">No sync history.</span>';
    } else {
        hist.innerHTML = '<table class="vdbx-table"><thead><tr><th>Source</th><th>Status</th><th>Fetched</th><th>Indexed</th><th>Time</th></tr></thead><tbody>' +
            history.map((h) => '<tr><td>' + h.connector + '</td><td><span class="vdbx-badge ' + badgeClass(h.status) + '">' + h.status + '</span></td><td>' + (h.fetched_count || 0) + '</td><td>' + (h.indexed_count || 0) + '</td><td>' + (h.created_at || '-') + '</td></tr>').join('') +
            '</tbody></table>';
    }
    if (statusEl && !statusEl.textContent) statusEl.textContent = "Ready.";
} catch (err) {
    conn.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
    hist.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

let editingConnectorId = null;

function setConnectorConsoleLines(lines) {
    const consoleEl = document.getElementById("vdbx-connector-console");
    if (!consoleEl) return;
    const normalized = (lines || []).map((line) => String(line || "")).filter(Boolean);
    consoleEl.classList.add("open");
    consoleEl.textContent = normalized.length ? normalized.join("
") : "No operation log returned.";
}

function appendConnectorConsoleLine(line) {
    const consoleEl = document.getElementById("vdbx-connector-console");
    if (!consoleEl) return;
    const ts = new Date().toISOString();
    const next = "[" + ts + "] " + String(line || "");
    consoleEl.classList.add("open");
    if (!consoleEl.textContent || consoleEl.textContent.indexOf("Source console ready") === 0) {
        consoleEl.textContent = next;
    } else {
        consoleEl.textContent = consoleEl.textContent + "
" + next;
    }
}

function readConnectorConfigJson() {
    const raw = (document.getElementById("vdbx-connector-config").value || "").trim();
    if (!raw) return {};
    return JSON.parse(raw);
}

function setConnectorForm(data) {
    const c = data || {};
    const cfg = c.config || {};
    document.getElementById("vdbx-connector-name").value = c.name || "";
    document.getElementById("vdbx-connector-type").value = c.connector_type || "rest_api";
    document.getElementById("vdbx-connector-base-url").value = c.base_url || "";
    document.getElementById("vdbx-connector-kb").value = c.knowledge_base_slug || "";
    document.getElementById("vdbx-connector-auth-type").value = c.auth_type || cfg.auth_type || "bearer";
    document.getElementById("vdbx-connector-sync-mode").value = c.sync_mode || cfg.sync_mode || "incremental";
    document.getElementById("vdbx-connector-token").value = "";
    document.getElementById("vdbx-connector-proxy").value = c.proxy_url || cfg.proxy_url || "";
    document.getElementById("vdbx-connector-endpoint-path").value = cfg.endpoint_path || "";
    document.getElementById("vdbx-connector-embedding").value = c.embedding_profile_slug || cfg.embedding_profile_slug || "";
    document.getElementById("vdbx-connector-interval").value = String(c.sync_interval_minutes || cfg.sync_interval_minutes || 30);
    document.getElementById("vdbx-connector-config").value = Object.keys(cfg).length ? JSON.stringify(cfg, null, 2) : "";
}

function collectConnectorPayload() {
    const cfg = readConnectorConfigJson();
    const endpointPath = (document.getElementById("vdbx-connector-endpoint-path").value || "").trim();
    if (endpointPath) cfg.endpoint_path = endpointPath;
    else delete cfg.endpoint_path;
    const proxyUrl = (document.getElementById("vdbx-connector-proxy").value || "").trim();
    if (proxyUrl) cfg.proxy_url = proxyUrl;
    else delete cfg.proxy_url;
    const payload = {
        name: (document.getElementById("vdbx-connector-name").value || "").trim(),
        connector_type: (document.getElementById("vdbx-connector-type").value || "rest_api").trim(),
        base_url: (document.getElementById("vdbx-connector-base-url").value || "").trim(),
        knowledge_base_slug: (document.getElementById("vdbx-connector-kb").value || "").trim(),
        auth_type: (document.getElementById("vdbx-connector-auth-type").value || "bearer").trim(),
        sync_mode: (document.getElementById("vdbx-connector-sync-mode").value || "incremental").trim(),
        sync_interval_minutes: Number(document.getElementById("vdbx-connector-interval").value || "30"),
        embedding_profile_slug: (document.getElementById("vdbx-connector-embedding").value || "").trim(),
        access_token: (document.getElementById("vdbx-connector-token").value || "").trim(),
        proxy_url: proxyUrl,
        config: cfg,
    };
    return payload;
}

async function saveConnector() {
    const statusEl = document.getElementById("vdbx-connector-status");
    try {
        appendConnectorConsoleLine("Saving source configuration...");
        const payload = collectConnectorPayload();
        if (!payload.name || !payload.base_url) {
            statusEl.textContent = "Name and Base URL are required.";
            statusEl.style.color = "#8b1e24";
            appendConnectorConsoleLine("Save blocked: Name and Base URL are required.");
            return;
        }
        const isEdit = !!editingConnectorId;
        const url = isEdit
            ? "/api/v1/vector-db/connectors/" + editingConnectorId + "/"
            : "/api/v1/vector-db/connectors/";
        const method = isEdit ? "PATCH" : "POST";
        const data = await api(url, {
            method,
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify(payload),
        });
        editingConnectorId = null;
        setConnectorForm({});
        statusEl.textContent = isEdit
            ? "Source updated successfully."
            : "Source created successfully.";
        statusEl.style.color = "#17663b";
        appendConnectorConsoleLine(statusEl.textContent);
        await loadSync();
        if (!isEdit && data.connector && data.connector.id) {
            appendConnectorConsoleLine("Running initial sync for new source #" + data.connector.id + "...");
            const syncData = await api("/api/v1/vector-db/connectors/" + data.connector.id + "/sync/", { method: "POST" });
            setConnectorConsoleLines(syncData.log || ["Initial sync completed."]);
            await loadSync();
        }
    } catch (err) {
        statusEl.textContent = "Save failed: " + err.message;
        statusEl.style.color = "#8b1e24";
        appendConnectorConsoleLine(statusEl.textContent);
    }
}

async function testConnectorConnection() {
    const statusEl = document.getElementById("vdbx-connector-status");
    if (!editingConnectorId) {
        statusEl.textContent = "Save the source first, then run Test Connection.";
        statusEl.style.color = "#8b1e24";
        appendConnectorConsoleLine(statusEl.textContent);
        return;
    }
    try {
        const data = await api("/api/v1/vector-db/connectors/" + editingConnectorId + "/test/", { method: "POST" });
        statusEl.textContent = data.detail || "Connection successful.";
        statusEl.style.color = "#17663b";
        setConnectorConsoleLines(data.log || [statusEl.textContent]);
    } catch (err) {
        statusEl.textContent = "Connection failed: " + err.message;
        statusEl.style.color = "#8b1e24";
        appendConnectorConsoleLine(statusEl.textContent);
    }
}

async function loadEmbedding() {
const el = document.getElementById("vdbx-embedding-monitor");
try {
    const data = await api("/api/v1/vector-db/embeddings/monitor/");
    const rows = data.results || [];
    if (!rows.length) {
        el.innerHTML = '<span class="vdbx-tip">No document ingestion records are available for your account.</span>';
        return;
    }
    el.innerHTML = '<table class="vdbx-table"><thead><tr><th>KB</th><th>Ingestion</th><th>Qdrant</th><th>Collection</th><th>Local Chunks</th><th>Qdrant Points</th><th>Details</th></tr></thead><tbody>' +
        rows.map((r) => '<tr><td>' + r.knowledge_base + '</td>' +
            '<td><span class="vdbx-badge ' + badgeClass(r.processing_status) + '">' + r.processing_status + '</span></td>' +
            '<td><span class="vdbx-badge ' + (r.qdrant_status === "connected" ? "vdbx-green" : "vdbx-red") + '">' + r.qdrant_status + '</span></td>' +
            '<td><span class="vdbx-badge ' + (r.collection_status === "available" ? "vdbx-green" : r.collection_status === "missing" ? "vdbx-amber" : "vdbx-red") + '">' + r.collection_status + '</span></td>' +
            '<td>' + (r.chunk_count || 0) + '</td><td>' + (r.qdrant_points || 0) + '</td><td class="vdbx-tip">' + (r.status_detail || '-') + '</td></tr>').join('') +
        '</tbody></table>';
} catch (err) {
    el.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function runSearch() {
const q = document.getElementById("vdbx-search-query").value.trim();
const kb = document.getElementById("vdbx-search-kb").value.trim();
const topK = Number(document.getElementById("vdbx-search-topk").value || "5");
const thresholdText = document.getElementById("vdbx-search-threshold").value.trim();
const out = document.getElementById("vdbx-search-results");
if (!q) {
    out.textContent = "Enter query first.";
    return;
}
out.textContent = "Searching...";
try {
    const body = { query: q, top_k: topK };
    if (kb) body.knowledge_base_slug = kb;
    if (thresholdText) body.score_threshold = Number(thresholdText);
    const data = await api("/api/v1/vector-db/search-playground/", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body),
    });
    const rows = data.results || [];
    if (!rows.length) {
        out.innerHTML = '<span class="vdbx-tip">No chunks retrieved.</span>';
        return;
    }
    out.innerHTML = rows.map((r) =>
        '<div class="vdbx-card" style="margin-top:8px;">' +
            '<h4>Score: ' + Number(r.score || 0).toFixed(4) + ' <span class="vdbx-badge vdbx-gray">' + (r.source || '-') + '</span></h4>' +
            '<div class="body"><div style="white-space:pre-wrap; font-size:12px; color:#29456b;">' + (r.text || '').replace(/</g, '&lt;') + '</div>' +
            '<div class="vdbx-tip" style="margin-top:6px;">Metadata: ' + JSON.stringify(r.metadata || {}) + '</div></div>' +
        '</div>'
    ).join('');
} catch (err) {
    out.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function loadMonitoring() {
const el = document.getElementById("vdbx-monitoring");
try {
    const data = await api("/api/v1/vector-db/system-monitoring/");
    const m = data.monitoring || {};
    const conn = m.qdrant_connectivity || {};
    const usage = m.collection_size_usage || [];
    const growth = m.vector_growth_trend || [];
    const errors = m.error_logs || [];

    const usageHtml = usage.length
        ? '<table class="vdbx-table"><thead><tr><th>Collection</th><th>Points</th><th>Vectors</th></tr></thead><tbody>' +
            usage.map((u) => '<tr><td>' + u.collection + '</td><td>' + u.points_count + '</td><td>' + u.vectors_count + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No collection usage data.</span>';

    const growthHtml = growth.length
        ? '<table class="vdbx-table"><thead><tr><th>Date</th><th>New Chunks</th></tr></thead><tbody>' +
            growth.map((g) => '<tr><td>' + g.date + '</td><td>' + g.new_chunks + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No growth trend data.</span>';

    const errHtml = errors.length
        ? '<table class="vdbx-table"><thead><tr><th>Action</th><th>Resource</th><th>Time</th></tr></thead><tbody>' +
            errors.map((e) => '<tr><td>' + e.action + '</td><td>' + (e.resource_type || '-') + ':' + (e.resource_id || '-') + '</td><td>' + (e.created_at || '-') + '</td></tr>').join('') +
            '</tbody></table>'
        : '<span class="vdbx-tip">No error logs.</span>';

    el.innerHTML =
        '<div class="vdbx-row2">' +
            '<div class="vdbx-card"><h4>Qdrant Connectivity</h4><div class="body">' +
                '<span class="vdbx-badge ' + badgeClass(conn.connected ? 'connected' : 'disconnected') + '">' + (conn.connected ? 'Connected' : 'Disconnected') + '</span>' +
                '<div class="vdbx-tip" style="margin-top:6px;">Latency: ' + (conn.latency_ms || 0) + 'ms</div>' +
                '<div class="vdbx-tip">Error: ' + (conn.error || 'none') + '</div>' +
            '</div></div>' +
            '<div class="vdbx-card"><h4>Vector Growth Trend</h4><div class="body">' + growthHtml + '</div></div>' +
        '</div>' +
        '<div class="vdbx-card"><h4>Collection Size Usage</h4><div class="body">' + usageHtml + '</div></div>' +
        '<div class="vdbx-card"><h4>Error Logs</h4><div class="body">' + errHtml + '</div></div>';
} catch (err) {
    el.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

shell.addEventListener("click", async function(evt){
const actionBtn = evt.target.closest("button[data-action]");
if (actionBtn) {
    await collectionAction(actionBtn.getAttribute("data-action"), actionBtn.getAttribute("data-slug"));
    return;
}
const syncBtn = evt.target.closest("button[data-resync]");
if (syncBtn) {
    const id = syncBtn.getAttribute("data-resync");
    try {
        const data = await api("/api/v1/vector-db/sync/" + id + "/resync/", { method: "POST" });
        setConnectorConsoleLines([
            "[MANUAL RESYNC] Connector #" + id,
            "Status: " + (data.status || "triggered"),
            "Fetched: " + (data.fetched_count || 0),
            "Indexed: " + (data.indexed_count || 0),
            "Detail: " + (data.detail || "Re-sync triggered."),
        ]);
        await loadSync();
    } catch (err) {
        appendConnectorConsoleLine("Re-sync failed: " + err.message);
        window.alert("Re-sync failed: " + err.message);
    }
    return;
}
const editConnectorBtn = evt.target.closest("button[data-edit-connector]");
if (editConnectorBtn) {
    const id = editConnectorBtn.getAttribute("data-edit-connector");
    try {
        const data = await api("/api/v1/vector-db/connectors/" + id + "/");
        editingConnectorId = id;
        setConnectorForm(data.connector || {});
        const statusEl = document.getElementById("vdbx-connector-status");
        statusEl.textContent = "Editing source #" + id + ". Save to apply changes.";
        statusEl.style.color = "#224774";
        appendConnectorConsoleLine("Loaded source #" + id + " into the form.");
    } catch (err) {
        window.alert("Unable to load source: " + err.message);
    }
    return;
}
const testConnectorBtn = evt.target.closest("button[data-test-connector]");
if (testConnectorBtn) {
    const id = testConnectorBtn.getAttribute("data-test-connector");
    try {
        const data = await api("/api/v1/vector-db/connectors/" + id + "/test/", { method: "POST" });
        const statusEl = document.getElementById("vdbx-connector-status");
        statusEl.textContent = "Source test success: " + (data.detail || "Connection successful.");
        statusEl.style.color = "#17663b";
        setConnectorConsoleLines(data.log || [statusEl.textContent]);
    } catch (err) {
        const statusEl = document.getElementById("vdbx-connector-status");
        statusEl.textContent = "Source test failed: " + err.message;
        statusEl.style.color = "#8b1e24";
        appendConnectorConsoleLine(statusEl.textContent);
    }
    return;
}
const syncConnectorBtn = evt.target.closest("button[data-sync-connector]");
if (syncConnectorBtn) {
    const id = syncConnectorBtn.getAttribute("data-sync-connector");
    try {
        const data = await api("/api/v1/vector-db/connectors/" + id + "/sync/", { method: "POST" });
        const statusEl = document.getElementById("vdbx-connector-status");
        statusEl.textContent = "Source sync status: " + (data.status || "completed");
        statusEl.style.color = String(data.status || "").toLowerCase() === "failed" ? "#8b1e24" : "#17663b";
        setConnectorConsoleLines(data.log || [statusEl.textContent]);
        await Promise.all([loadSync(), loadDashboard()]);
    } catch (err) {
        appendConnectorConsoleLine("Sync failed: " + err.message);
        window.alert("Sync failed: " + err.message);
    }
    return;
}
const deleteConnectorBtn = evt.target.closest("button[data-delete-connector]");
if (deleteConnectorBtn) {
    const id = deleteConnectorBtn.getAttribute("data-delete-connector");
    if (!window.confirm("Delete this source configuration?")) return;
    try {
        await api("/api/v1/vector-db/connectors/" + id + "/", { method: "DELETE" });
        if (String(editingConnectorId || "") === String(id)) {
            editingConnectorId = null;
            setConnectorForm({});
        }
        await loadSync();
    } catch (err) {
        window.alert("Delete failed: " + err.message);
    }
    return;
}
const whyBtn = evt.target.closest("button[data-why-toggle]");
if (whyBtn) {
    const panel = document.getElementById("vdbx-why-" + whyBtn.getAttribute("data-why-toggle"));
    if (panel) panel.classList.toggle("open");
    return;
}
const selectBtn = evt.target.closest("button[data-select-provider]");
if (selectBtn) {
    const slug = selectBtn.getAttribute("data-select-provider");
    const embeddingEl = document.getElementById("vdbx-upload-embedding");
    if (embeddingEl) embeddingEl.value = slug;
    highlightSelectedProvider(slug);
    return;
}
const configureBtn = evt.target.closest("button[data-configure-provider]");
if (configureBtn) {
    openProviderConnectionModal(configureBtn.getAttribute("data-configure-provider"));
    return;
}
const selectReasoningBtn = evt.target.closest("button[data-select-reasoning]");
if (selectReasoningBtn) {
    await selectReasoningProfile(selectReasoningBtn.getAttribute("data-select-reasoning"));
    return;
}
const configureReasoningBtn = evt.target.closest("button[data-configure-reasoning]");
if (configureReasoningBtn) {
    openReasoningConnectionModal(configureReasoningBtn.getAttribute("data-configure-reasoning"));
    return;
}
});

bindEvent("vdbx-search-run", "click", runSearch);
bindEvent("vdbx-create-collection", "click", createCollectionFlow);
bindEvent("vdbx-collections-refresh", "click", loadCollections);
bindEvent("vdbx-connector-save", "click", saveConnector);
bindEvent("vdbx-connector-test", "click", testConnectorConnection);
bindEvent("vdbx-connector-reset", "click", () => {
    editingConnectorId = null;
    setConnectorForm({});
    const statusEl = document.getElementById("vdbx-connector-status");
    statusEl.textContent = "Form reset. Ready for new source.";
    statusEl.style.color = "#224774";
    setConnectorConsoleLines(["Source console ready. Run Test Connection or Sync to view logs."]);
});
bindEvent("vdbx-refresh-all", "click", async () => {
await Promise.all([loadDashboard(), loadCollections(), loadUploads(), loadSync(), loadEmbedding(), loadMonitoring(), loadReasoningProfiles()]);
});

const compareModal = document.getElementById("vdbx-compare-modal");
bindEvent("vdbx-compare-providers", "click", () => {
const bodyEl = document.getElementById("vdbx-compare-body");
if (bodyEl) bodyEl.innerHTML = buildCompareTable();
if (compareModal) compareModal.classList.add("open");
});
bindEvent("vdbx-compare-close", "click", () => { if (compareModal) compareModal.classList.remove("open"); });
bindEvent("vdbx-compare-done", "click", () => { if (compareModal) compareModal.classList.remove("open"); });
if (compareModal) compareModal.addEventListener("click", (event) => { if (event.target === compareModal) compareModal.classList.remove("open"); });
bindEvent("vdbx-upload-embedding", "change", (event) => {
highlightSelectedProvider(event.target.value);
});

let providerConnSlug = null;
const providerConnModal = document.getElementById("vdbx-provider-conn-modal");

function updateProviderDot(slug, available) {
const dot = document.getElementById("vdbx-dot-" + slug);
if (!dot) return;
dot.classList.toggle("vdbx-dot-green", available);
dot.classList.toggle("vdbx-dot-red", !available);
dot.title = available ? "Available" : "Not configured";
const cached = embeddingProfilesCache.find((p) => p.slug === slug);
if (cached) cached.is_configured = available;
}

function openProviderConnectionModal(slug) {
const profile = embeddingProfilesCache.find((p) => p.slug === slug);
if (!profile) return;
providerConnSlug = slug;
document.getElementById("vdbx-provider-conn-title").textContent = "Configure " + profile.name;
document.getElementById("vdbx-provider-conn-url").value = profile.base_url || "";
document.getElementById("vdbx-provider-conn-key").value = "";
document.getElementById("vdbx-provider-conn-key").placeholder = profile.api_key_masked ? profile.api_key_masked + " - leave blank to keep it" : "No key set yet";
document.getElementById("vdbx-provider-conn-proxy").value = profile.proxy_url || "";
document.getElementById("vdbx-provider-conn-timeout").value = profile.connection_timeout_seconds || 10;
document.getElementById("vdbx-provider-conn-status").textContent = "Not tested yet.";
document.getElementById("vdbx-provider-conn-error").textContent = "";
const consoleEl = document.getElementById("vdbx-provider-conn-console");
consoleEl.textContent = 'Click "Console" to run a diagnostic request and see exactly what is sent and received.';
consoleEl.classList.remove("open");
providerConnModal.classList.add("open");
}

async function submitProviderConnection(save) {
if (!providerConnSlug) return;
const button = save ? document.getElementById("vdbx-provider-conn-save") : document.getElementById("vdbx-provider-conn-test");
const originalText = button.textContent;
const errorEl = document.getElementById("vdbx-provider-conn-error");
const statusEl = document.getElementById("vdbx-provider-conn-status");
button.disabled = true;
button.textContent = save ? "Saving..." : "Testing...";
errorEl.textContent = "";
try {
    const body = {
        base_url: document.getElementById("vdbx-provider-conn-url").value.trim(),
        api_key: document.getElementById("vdbx-provider-conn-key").value.trim(),
        proxy_url: document.getElementById("vdbx-provider-conn-proxy").value.trim(),
        connection_timeout_seconds: Number(document.getElementById("vdbx-provider-conn-timeout").value || "10"),
        save: !!save,
    };
    const request = save ? {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body),
    } : {
        method: "GET",
        headers: {
            "X-Embedding-Base-Url": body.base_url,
            "X-Embedding-Api-Key": body.api_key,
            "X-Embedding-Proxy-Url": body.proxy_url,
            "X-Embedding-Timeout": String(body.connection_timeout_seconds),
        },
    };
    const data = await api("/api/v1/embedding-profiles/" + providerConnSlug + "/connection/", request);
    statusEl.innerHTML = '<span class="vdbx-badge ' + (data.available ? "vdbx-green" : "vdbx-red") + '">' + (data.available ? "Available" : "Unavailable") + '</span> ' +
        '<span class="vdbx-tip">' + (data.detail || "") + (data.latency_ms ? " (" + data.latency_ms + "ms)" : "") + '</span>';
    document.getElementById("vdbx-provider-conn-console").textContent = (data.log && data.log.length) ? data.log.join("\n") : "No diagnostic output returned.";
    updateProviderDot(providerConnSlug, data.available);
    if (save) {
        if (data.profile) {
            const idx = embeddingProfilesCache.findIndex((p) => p.slug === providerConnSlug);
            if (idx >= 0) embeddingProfilesCache[idx] = data.profile;
        }
        providerConnModal.classList.remove("open");
    }
} catch (err) {
    errorEl.textContent = err.message;
} finally {
    button.disabled = false;
    button.textContent = originalText;
}
}

bindEvent("vdbx-provider-conn-close", "click", () => { if (providerConnModal) providerConnModal.classList.remove("open"); });
bindEvent("vdbx-provider-conn-test", "click", () => submitProviderConnection(false));
bindEvent("vdbx-provider-conn-save", "click", () => submitProviderConnection(true));
bindEvent("vdbx-provider-conn-console-btn", "click", async () => {
const consoleEl = document.getElementById("vdbx-provider-conn-console");
consoleEl.classList.add("open");
consoleEl.textContent = "Running diagnostic request...";
await submitProviderConnection(false);
});
if (providerConnModal) providerConnModal.addEventListener("click", (event) => { if (event.target === providerConnModal) providerConnModal.classList.remove("open"); });

let reasoningConnSlug = null;
const reasoningConnModal = document.getElementById("vdbx-reasoning-conn-modal");

function openReasoningConnectionModal(slug) {
const profile = reasoningProfilesCache.find((p) => p.slug === slug);
if (!profile) return;
reasoningConnSlug = slug;
document.getElementById("vdbx-reasoning-conn-title").textContent = "Configure " + profile.name;
document.getElementById("vdbx-reasoning-conn-url").value = profile.endpoint_url || "";
document.getElementById("vdbx-reasoning-conn-model").value = profile.model_name || "";
document.getElementById("vdbx-reasoning-conn-key").value = "";
document.getElementById("vdbx-reasoning-conn-timeout").value = profile.timeout_seconds || 60;
document.getElementById("vdbx-reasoning-conn-status").textContent = "Not tested yet.";
document.getElementById("vdbx-reasoning-conn-error").textContent = "";
reasoningConnModal.classList.add("open");
}

async function submitReasoningConnection(save) {
if (!reasoningConnSlug) return;
const button = save ? document.getElementById("vdbx-reasoning-conn-save") : document.getElementById("vdbx-reasoning-conn-test");
const originalText = button.textContent;
const errorEl = document.getElementById("vdbx-reasoning-conn-error");
const statusEl = document.getElementById("vdbx-reasoning-conn-status");
button.disabled = true;
button.textContent = save ? "Saving..." : "Testing...";
errorEl.textContent = "";
try {
    const body = {
        endpoint_url: document.getElementById("vdbx-reasoning-conn-url").value.trim(),
        model_name: document.getElementById("vdbx-reasoning-conn-model").value.trim(),
        api_key: document.getElementById("vdbx-reasoning-conn-key").value.trim(),
        timeout_seconds: Number(document.getElementById("vdbx-reasoning-conn-timeout").value || "60"),
        save: !!save,
    };
    const data = await api("/api/v1/reasoning-profiles/" + reasoningConnSlug + "/connection/", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(body),
    });
    statusEl.innerHTML = '<span class="vdbx-badge ' + (data.available ? "vdbx-green" : "vdbx-red") + '">' + (data.available ? "Available" : "Unavailable") + '</span> ' +
        '<span class="vdbx-tip">' + (data.detail || "") + '</span>';
    if (save) {
        reasoningConnModal.classList.remove("open");
        await loadReasoningProfiles();
    }
} catch (err) {
    errorEl.textContent = err.message;
} finally {
    button.disabled = false;
    button.textContent = originalText;
}
}

async function selectReasoningProfile(slug) {
try {
    await api("/api/v1/reasoning-profiles/" + slug + "/connection/", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({set_default: true}),
    });
    await loadReasoningProfiles();
} catch (err) {
    window.alert("Unable to set reasoning profile: " + err.message);
}
}

bindEvent("vdbx-reasoning-conn-close", "click", () => { if (reasoningConnModal) reasoningConnModal.classList.remove("open"); });
bindEvent("vdbx-reasoning-conn-test", "click", () => submitReasoningConnection(false));
bindEvent("vdbx-reasoning-conn-save", "click", () => submitReasoningConnection(true));
if (reasoningConnModal) reasoningConnModal.addEventListener("click", (event) => { if (event.target === reasoningConnModal) reasoningConnModal.classList.remove("open"); });

async function loadKnowledgeBaseOptions() {
try {
    const data = await api("/api/v1/knowledge-bases/");
    const kbs = data.results || [];
    const uploadSelect = document.getElementById("vdbx-upload-kb");
    const connSelect = document.getElementById("vdbx-conn-default-kb");
    const connectorKbSelect = document.getElementById("vdbx-connector-kb");
    const uploadOptions = ['<option value="">Use default collection</option>'].concat(
        kbs.map((kb) => '<option value="' + kb.slug + '">' + kb.name + ' (' + kb.collection + ')</option>')
    ).join('');
    const connOptions = ['<option value="">No default</option>'].concat(
        kbs.map((kb) => '<option value="' + kb.slug + '">' + kb.name + ' (' + kb.collection + ')</option>')
    ).join('');
    const connectorOptions = ['<option value="">Use default knowledge base</option>'].concat(
        kbs.map((kb) => '<option value="' + kb.slug + '">' + kb.name + ' (' + kb.collection + ')</option>')
    ).join('');
    if (uploadSelect) uploadSelect.innerHTML = uploadOptions;
    if (connSelect) connSelect.innerHTML = connOptions;
    if (connectorKbSelect) connectorKbSelect.innerHTML = connectorOptions;
} catch (err) {
    /* Selects fall back to the default-only option if this fails. */
}
}

async function loadConnectorEmbeddingOptions() {
try {
    const data = await api("/api/v1/embedding-profiles/?scope=settings");
    const rows = data.results || [];
    const select = document.getElementById("vdbx-connector-embedding");
    if (!select) return;
    select.innerHTML = ['<option value="">Use default embedding</option>']
        .concat(rows.map((r) => '<option value="' + r.slug + '">' + r.name + ' (' + (r.provider_type_display || r.provider_type || '-') + ')</option>'))
        .join('');
} catch (_err) {
    /* Keep default option if unavailable */
}
}

let embeddingProfilesCache = [];
let reasoningProfilesCache = [];

function costLabel(cost) {
const map = {free: "Free", low: "Low Cost", medium: "Medium Cost", high: "High Cost"};
return map[cost] || cost;
}

function capabilityLabel(capability) {
const map = {online: "Online (Cloud)", offline: "Offline (Local)", hybrid: "Hybrid"};
return map[capability] || capability;
}

function starRating(rating) {
const filled = Math.max(0, Math.min(5, Number(rating) || 0));
return "&#9733;".repeat(filled) + "&#9734;".repeat(5 - filled);
}

function providerCardHtml(profile, isDefault) {
const badgesHtml = (profile.badges || []).map((b) =>
    '<span class="vdbx-provider-badge">' + b.icon + ' ' + b.label + '</span>'
).join('');
const highlightsHtml = (profile.highlights || []).map((h) =>
    '<li>&#10003; ' + h + '</li>'
).join('');
const dotClass = profile.is_configured ? "vdbx-dot-green" : "vdbx-dot-red";
const dotLabel = profile.is_configured ? "Available" : "Not configured";
return (
    '<div class="vdbx-provider-card" data-provider-slug="' + profile.slug + '">' +
        '<div class="vdbx-provider-head">' +
            '<div><div class="vdbx-provider-name">' +
                '<span class="vdbx-status-dot ' + dotClass + '" id="vdbx-dot-' + profile.slug + '" title="' + dotLabel + '"></span>' +
                profile.name + (isDefault ? ' <span class="vdbx-tip">(default)</span>' : '') +
            '</div>' +
            '<div class="vdbx-provider-model">' + (profile.model_name || 'Model not specified') + '</div></div>' +
        '</div>' +
        (badgesHtml ? '<div class="vdbx-provider-badges">' + badgesHtml + '</div>' : '') +
        '<div class="vdbx-provider-meta">' +
            '<div><strong>Dimensions</strong>' + (profile.embedding_dimensions || '-') + '</div>' +
            '<div><strong>Performance</strong><span class="vdbx-stars">' + starRating(profile.performance_rating) + '</span></div>' +
            '<div><strong>Cost</strong>' + costLabel(profile.cost_indicator) + '</div>' +
            '<div><strong>Capability</strong>' + capabilityLabel(profile.capability) + '</div>' +
        '</div>' +
        (highlightsHtml ? '<ul class="vdbx-provider-highlights">' + highlightsHtml + '</ul>' : '') +
        (profile.why_choose ? (
            '<button type="button" class="vdbx-provider-why-toggle" data-why-toggle="' + profile.slug + '">Why choose this provider?</button>' +
            '<div class="vdbx-provider-why" id="vdbx-why-' + profile.slug + '">' + profile.why_choose + '</div>'
        ) : '') +
        '<div class="vdbx-row2" style="margin-top:8px;">' +
            '<button type="button" class="vdbx-btn vdbx-provider-select-btn" data-select-provider="' + profile.slug + '">Use this profile</button>' +
            (profile.provider_type === "default"
                ? ''
                : '<button type="button" class="vdbx-btn" data-configure-provider="' + profile.slug + '">Configure</button>') +
        '</div>' +
    '</div>'
);
}

function highlightSelectedProvider(slug) {
document.querySelectorAll(".vdbx-provider-card").forEach((card) => {
    card.classList.toggle("selected", card.getAttribute("data-provider-slug") === slug);
});
}

function reasoningProviderCardHtml(profile, isSelected) {
const dotClass = profile.is_selected ? "vdbx-dot-green" : "vdbx-dot-red";
const dotLabel = profile.is_selected ? "Selected" : "Not selected";
return (
    '<div class="vdbx-provider-card' + (isSelected ? ' selected' : '') + '" data-reasoning-slug="' + profile.slug + '">' +
        '<div class="vdbx-provider-head">' +
            '<div><div class="vdbx-provider-name">' +
                '<span class="vdbx-status-dot ' + dotClass + '" title="' + dotLabel + '"></span>' +
                profile.name + (isSelected ? ' <span class="vdbx-tip">(active)</span>' : '') +
            '</div>' +
            '<div class="vdbx-provider-model">' + (profile.model_name || 'Model not specified') + '</div></div>' +
        '</div>' +
        '<div class="vdbx-provider-meta">' +
            '<div><strong>Provider</strong>' + (profile.provider_type || '-') + '</div>' +
            '<div><strong>Timeout</strong>' + (profile.timeout_seconds || 60) + 's</div>' +
            '<div><strong>Temperature</strong>' + (profile.temperature || 0) + '</div>' +
            '<div><strong>Max Tokens</strong>' + (profile.max_tokens || '-') + '</div>' +
        '</div>' +
        '<div class="vdbx-tip" style="margin-bottom:8px;">' + (profile.endpoint_url || 'No endpoint configured') + '</div>' +
        '<div class="vdbx-row2" style="margin-top:8px;">' +
            '<button type="button" class="vdbx-btn vdbx-provider-select-btn" data-select-reasoning="' + profile.slug + '">Use for chat</button>' +
            '<button type="button" class="vdbx-btn" data-configure-reasoning="' + profile.slug + '">Configure</button>' +
        '</div>' +
    '</div>'
);
}

async function loadReasoningProfiles() {
const cardsEl = document.getElementById("vdbx-reasoning-cards");
if (!cardsEl) return;
try {
    const data = await api("/api/v1/reasoning-profiles/");
    if (data.enabled === false) {
        reasoningProfilesCache = [];
        cardsEl.innerHTML = '<span class="vdbx-tip">Reasoning provider profiles are disabled from AI Provider settings.</span>';
        return;
    }

    reasoningProfilesCache = data.results || [];
    const selectedSlug = data.default_slug || "";

    if (!reasoningProfilesCache.length) {
        cardsEl.innerHTML = '<span class="vdbx-tip">No reasoning provider profiles configured yet.</span>';
        return;
    }

    cardsEl.innerHTML = reasoningProfilesCache.map((p) => reasoningProviderCardHtml(p, p.slug === selectedSlug)).join('');
} catch (err) {
    cardsEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function loadEmbeddingProfiles() {
const cardsEl = document.getElementById("vdbx-provider-cards");
const selectEl = document.getElementById("vdbx-upload-embedding");
try {
    const data = await api("/api/v1/embedding-profiles/");
    if (data.enabled === false) {
        embeddingProfilesCache = [];
        if (selectEl) {
            selectEl.innerHTML = '<option value="">Embedding profiles disabled</option>';
            selectEl.disabled = true;
        }
        cardsEl.innerHTML = '<span class="vdbx-tip">Embedding provider profiles are disabled from AI Provider settings.</span>';
        return;
    }

    embeddingProfilesCache = data.results || [];
    const defaultSlug = data.default_slug || "";

    if (selectEl) {
        selectEl.disabled = false;
        selectEl.innerHTML = ['<option value="">Use default embedding</option>'].concat(
            embeddingProfilesCache.map((p) => '<option value="' + p.slug + '">' + p.name + '</option>')
        ).join('');
    }

    if (!embeddingProfilesCache.length) {
        cardsEl.innerHTML = '<span class="vdbx-tip">No embedding profiles configured yet.</span>';
        return;
    }

    cardsEl.innerHTML = embeddingProfilesCache.map((p) => providerCardHtml(p, p.slug === defaultSlug)).join('');
} catch (err) {
    cardsEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

function buildCompareTable() {
if (!embeddingProfilesCache.length) {
    return '<span class="vdbx-tip">No embedding profiles configured yet.</span>';
}
const rows = embeddingProfilesCache.map((p) =>
    '<tr>' +
        '<td><strong>' + p.name + '</strong></td>' +
        '<td>' + (p.model_name || '-') + '</td>' +
        '<td>' + (p.embedding_dimensions || '-') + '</td>' +
        '<td><span class="vdbx-stars">' + starRating(p.performance_rating) + '</span></td>' +
        '<td>' + costLabel(p.cost_indicator) + '</td>' +
        '<td>' + capabilityLabel(p.capability) + '</td>' +
        '<td>' + (p.best_use_case || '-') + '</td>' +
    '</tr>'
).join('');
return '<table class="vdbx-compare-table"><thead><tr>' +
    '<th>Provider</th><th>Model</th><th>Dimensions</th><th>Performance</th><th>Cost</th><th>Capability</th><th>Best Use Case</th>' +
    '</tr></thead><tbody>' + rows + '</tbody></table>';
}

function applyConnectionInfo(data) {
const badge = document.getElementById("vdbx-connection-badge");
const urlSmall = document.getElementById("vdbx-connection-url");
const statusEl = document.getElementById("vdbx-connection-status");
const status = data.connected ? "Connected" : "Disconnected";
if (badge) { badge.textContent = status; badge.className = "vdbx-badge " + badgeClass(status); }
if (urlSmall) urlSmall.textContent = "URL: " + (data.qdrant_url || "not set");
if (statusEl) {
    statusEl.innerHTML = data.connected
        ? '<span class="vdbx-badge vdbx-green">Connected</span> <span class="vdbx-tip">' + (data.collections_found || 0) + ' collection(s) visible from this URL.</span>'
        : '<span class="vdbx-badge vdbx-red">Disconnected</span> <span class="vdbx-tip">' + (data.error || 'Cannot reach Qdrant.') + '</span>';
}
}

async function loadConnection() {
try {
    const data = await api("/api/v1/vector-db/connection/");
    document.getElementById("vdbx-conn-url").value = data.qdrant_url || "";
    document.getElementById("vdbx-conn-timeout").value = data.qdrant_timeout_seconds || 30;
    document.getElementById("vdbx-conn-grpc").checked = !!data.qdrant_prefer_grpc;
    const kbSelect = document.getElementById("vdbx-conn-default-kb");
    if (kbSelect && data.default_knowledge_base_slug) kbSelect.value = data.default_knowledge_base_slug;
    applyConnectionInfo(data);
} catch (err) {
    const statusEl = document.getElementById("vdbx-connection-status");
    if (statusEl) statusEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
}
}

async function testOrSaveConnection(persist) {
const button = persist ? document.getElementById("vdbx-conn-save") : document.getElementById("vdbx-conn-test");
const originalText = button.textContent;
button.disabled = true;
button.textContent = persist ? "Saving..." : "Testing...";
try {
    const body = {
        qdrant_url: document.getElementById("vdbx-conn-url").value.trim(),
        qdrant_api_key: document.getElementById("vdbx-conn-key").value.trim(),
        qdrant_prefer_grpc: document.getElementById("vdbx-conn-grpc").checked,
        qdrant_timeout_seconds: Number(document.getElementById("vdbx-conn-timeout").value || "30"),
    };
    if (persist) {
        body.default_knowledge_base_slug = document.getElementById("vdbx-conn-default-kb").value;
    }
    const data = persist
        ? await api("/api/v1/vector-db/connection/", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) })
        : await api("/api/v1/vector-db/connection/");
    applyConnectionInfo(data);
    if (persist) {
        document.getElementById("vdbx-conn-key").value = "";
        await loadDashboard();
    }
} catch (err) {
    const statusEl = document.getElementById("vdbx-connection-status");
    if (statusEl) statusEl.innerHTML = '<span class="vdbx-badge vdbx-red">Error</span> ' + err.message;
} finally {
    button.disabled = false;
    button.textContent = originalText;
}
}

bindEvent("vdbx-conn-test", "click", () => testOrSaveConnection(false));
bindEvent("vdbx-conn-save", "click", () => testOrSaveConnection(true));
bindEvent("vdbx-connection-shortcut", "click", () => setActive("connection"));

bindUpload();
loadKnowledgeBaseOptions();
loadConnectorEmbeddingOptions();
loadEmbeddingProfiles();
loadReasoningProfiles();
loadConnection();
Promise.all([loadDashboard(), loadCollections(), loadUploads(), loadSync(), loadEmbedding(), loadMonitoring()]);
})();
</script>