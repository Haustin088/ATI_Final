// =========================================================
// GLOBAL STATE
// =========================================================
let currentStep = 1;
let selectedCluster = null;
let isProcessing = false;
let cachedMedia = [];


// =========================================================
// INIT TINYMCE EDITORS
// =========================================================
function initEditors() {
    // Outline Editor (Step 2)
    tinymce.init({
        selector: "#outline-editor",
        height: 500,
        menubar: false,
        plugins: "lists link image table wordcount code",
        toolbar: "undo redo | bold italic underline | bullist numlist | link | table | code",
        placeholder: "Dàn ý sẽ hiển thị ở đây..."
    });

    // Script Editor (Step 3)
    tinymce.init({
        selector: "#script-editor",
        height: 600,
        menubar: false,
        plugins: "lists link table wordcount code",
        toolbar: "undo redo | bold italic underline | bullist numlist | table | code",
        placeholder: "Kịch bản sẽ hiển thị ở đây..."
    });
}


// =========================================================
// MAIN INITIALIZER — Only one!
// =========================================================
document.addEventListener("DOMContentLoaded", () => {
    initEditors();
    loadEditorCluster();
    setupEventListeners();
});


// =========================================================
// LOAD CLUSTER
// =========================================================
async function loadEditorCluster() {
    const params = new URLSearchParams(window.location.search);
    const groupId = parseInt(params.get("group_id"));

    if (isNaN(groupId)) {
        console.error("❌ No group_id in URL");
        return;
    }

    try {
        const res = await fetch("../backend/data/claims_grouped_summary.json");
        const groups = await res.json();
        selectedCluster = groups.find(x => x.group_id === groupId);

        if (!selectedCluster) {
            console.error("❌ Cluster not found:", groupId);
            return;
        }

        loadClusterData(selectedCluster);
    } catch (err) {
        console.error("❌ Error loading cluster:", err);
    }
}


// =========================================================
// DISPLAY CLUSTER CONTENT
// =========================================================
function loadClusterData(c) {
    document.getElementById("cluster-id").textContent = c.group_id;
    document.getElementById("cluster-topic").textContent = c.topic;
    document.getElementById("cluster-summary").textContent = c.summary;

    document.getElementById("cluster-reliability").textContent = c.avg_reliability.toFixed(2);
    document.getElementById("cluster-conflict").textContent = c.conflict ? "Có" : "Không";

    document.getElementById("cluster-keywords").innerHTML =
        c.keywords.map(k => `<span class="media-tag">${k}</span>`).join("");

    document.getElementById("cluster-entities").innerHTML =
        c.entities.map(e => `<span class="media-tag">${e}</span>`).join("");

    document.getElementById("cluster-claims").innerHTML =
        c.claims.map(cl => `<li>${cl}</li>`).join("");

    document.getElementById("cluster-sources").innerHTML =
        c.sources.map(src => `
            <li><a href="${src}" target="_blank" class="text-blue-600 underline">${src}</a></li>
        `).join("");
}


// =========================================================
// NAVIGATION
// =========================================================
function setupEventListeners() {
    document.getElementById("tab-step1").onclick = () => switchTab(1);
    document.getElementById("tab-step2").onclick = () => switchTab(2);
    document.getElementById("tab-step3").onclick = () => switchTab(3);

    document.getElementById("next-to-step2").onclick = () => switchTab(2);
    document.getElementById("next-to-step3").onclick = () => switchTab(3);

    document.getElementById("generate-outline-btn").onclick = generateOutline;
    document.getElementById("generate-script-btn").onclick = generateScript;
    document.getElementById("export-pdf-btn")?.addEventListener("click", exportPDF);
}

function switchTab(step) {
    currentStep = step;

    document.querySelectorAll(".tab-button").forEach((btn, i) => {
        btn.classList.toggle("active", i + 1 === step);
    });

    for (let i = 1; i <= 3; i++) {
        document
            .getElementById(`content-step${i}`)
            .classList.toggle("hidden", i !== step);
    }

    // Fix TinyMCE not detecting editor in hidden tabs
    if (step === 3) {
        setTimeout(() => {
            tinymce.get("script-editor")?.focus();
        }, 50);
    }
}


// =========================================================
// STEP 2 — GENERATE OUTLINE
// =========================================================
async function generateOutline() {
    if (!selectedCluster || isProcessing) return;
    isProcessing = true;

    const btn = document.getElementById("generate-outline-btn");
    const oldHTML = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<div class="loading-spinner mx-auto"></div>';

    try {
        // ====== Get Article ======
        const res = await fetch("http://localhost:8000/api/generate_article", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(selectedCluster)
        });
        const data = await res.json();

        tinymce.get("outline-editor").setContent(formatArticle(data.article));


        // ====== Load Media from JSON ======
        const mediaRes = await fetch("../backend/data/suggested_media_output.json");
        const mediaFile = await mediaRes.json();

        const entry = mediaFile.find(x => x.group_id === selectedCluster.group_id);
        cachedMedia = entry ? entry.media : [];

        document.getElementById("media-suggestions").innerHTML =
            cachedMedia.length
                ? cachedMedia.map(m => `
                    <div class="border p-4 rounded-lg mb-3 bg-white shadow-sm">
                        <img src="${m.path}" onerror="this.src='${m.source}'"
                             class="rounded-md mb-2 max-h-48 object-cover w-full">
                        <p><b>Caption:</b> ${m.caption}</p>
                    </div>
                `).join("")
                : `<p class="text-gray-500 italic">Không có hình ảnh.</p>`;

        showToast("Đã tạo dàn ý!", "success");

    } catch (err) {
        console.error(err);
        showToast("❌ Lỗi khi tạo dàn ý", "error");
    }

    btn.disabled = false;
    btn.innerHTML = oldHTML;
    isProcessing = false;
}


// =========================================================
// STEP 3 — GENERATE FINAL SCRIPT
// =========================================================
async function generateScript() {
    const html = tinymce.get("outline-editor").getContent();
    const outlineText = htmlToTextWithNewlines(html);
    const format = document.getElementById("script-format").value;

    console.log(outlineText)


    try {
        const res = await fetch("http://localhost:8000/api/generate_script", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                cluster: selectedCluster,
                outline: outlineText,   // <-- fixed
                media: cachedMedia,
                format: format
            })
        });

        const data = await res.json();
        tinymce.get("script-editor").setContent(formatScript(data.script));

    } catch (err) {
        console.error(err);
        showToast("❌ Lỗi tạo kịch bản", "error");
    }
}

function htmlToTextWithNewlines(html) {
    html = html.replace(/<br\s*\/?>/gi, "\n");
    html = html.replace(/<\/p>/gi, "\n");
    html = html.replace(/<\/li>/gi, "\n");
    html = html.replace(/<[^>]+>/g, "");
    return html.replace(/\n\s*\n+/g, "\n").trim();
}
// =========================================================
// EXPORT PDF (html2pdf)
// =========================================================
function exportPDF() {
    const iframeBody = document.querySelector("#script-editor_ifr").contentDocument.body;

    const opt = {
        margin: 10,
        filename: "script.pdf",
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" }
    };

    html2pdf().from(iframeBody).set(opt).save();
}


// =========================================================
// HELPERS
// =========================================================
function formatArticle(text) {
    return text.split("\n").map(line => {
        if (line.startsWith("###")) {
            return `<h3 style="color:#764ba2;font-weight:bold;margin-top:20px">${line.replace("###", "")}</h3>`;
        }
        return `<p>${line}</p>`;
    }).join("");
}

function formatScript(text) {
    // 1) Convert markdown-like headers and bold and media tags in the whole text first
    let converted = text
        .replace(/^### (.*)$/gm, '<h3 class="text-xl font-bold mt-4 mb-2">$1</h3>')
        .replace(/^## (.*)$/gm, '<h2 class="text-2xl font-bold mt-4 mb-3">$1</h2>')
        .replace(/^# (.*)$/gm, '<h1 class="text-3xl font-bold mt-6 mb-4">$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\[(.*?)\]\s*(.*)/g,
            '<div class="script-line"><span class="media-tag">[$1]</span> <span>$2</span></div>'
        );

    // 2) Split by table blocks and only wrap paragraphs for non-table parts
    const parts = converted.split(/(<table[\s\S]*?<\/table>)/i); // keep the table blocks
    for (let i = 0; i < parts.length; i++) {
        if (parts[i].trim().length === 0) continue;

        if (/^<table/i.test(parts[i])) {
            // leave table HTML untouched
            continue;
        } else {
            // Wrap lines that are not already HTML block tags
            parts[i] = parts[i].replace(/^(?!\s*<(h\d|div|ul|ol|li|table|tr|td|th|p|blockquote|pre|img))(.+)$/gm,
                '<p class="mb-3">$2</p>');
        }
    }

    return parts.join("");
}

function showToast(msg, type = "info") {
    const el = document.createElement("div");
    el.className = `fixed bottom-6 right-6 px-6 py-3 rounded-lg shadow text-white 
                    ${type === "success" ? "bg-green-500" : "bg-blue-500"}`;
    el.textContent = msg;
    document.body.appendChild(el);

    setTimeout(() => el.remove(), 2500);
}
