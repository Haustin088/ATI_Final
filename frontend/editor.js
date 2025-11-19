async function loadClaimGroups() {
  const container = document.querySelector(".lg\\:col-span-2");
  if (!container) return;

  try {
    const res = await fetch("../backend/data/claims_grouped_summary.json");
    const groups = await res.json();

    groups.sort((a, b) => b.avg_reliability - a.avg_reliability);

    container.innerHTML = "";

    groups.forEach((g) => {
      const div = document.createElement("div");
      div.className =
        "bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer fade-in";
      div.innerHTML = `
        <div class="p-6">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-blue-600 rounded flex items-center justify-center">
                <span class="text-white font-bold text-xs">${(g.topic || "?").slice(0, 2).toUpperCase()}</span>
              </div>
              <div>
                <p class="font-medium text-gray-800">${g.topic || "Không rõ chủ đề"}</p>
                <p class="text-sm text-gray-500">${g.sources.length} nguồn</p>
              </div>
            </div>
            <div class="flex items-center space-x-2">
              ${
                g.conflict
                  ? `<span class="bg-red-100 text-red-800 px-2.5 py-1.5 rounded-full text-xs font-medium">⚠️ Mâu thuẫn</span>`
                  : `<span class="bg-green-100 text-green-800 px-2.5 py-1.5  rounded-full text-xs font-medium">Không mâu thuẫn</span>`
              }
              <span class="bg-blue-100 text-blue-800 px-2.5 py-1.5 rounded-full text-xs font-medium">Độ tin cậy: ${(
                g.avg_reliability * 100
              ).toFixed(0)}%</span>
            </div>
          </div>

          <h3 class="text-lg font-bold text-gray-800 mb-3 line-clamp-2">
            ${g.summary}
          </h3>

          <p class="text-gray-600 mb-4 line-clamp-3">
            ${g.claims.slice(0, 3).join(" ")}${g.claims.length > 3 ? "..." : ""}
          </p>

          <div class="bg-blue-50 rounded-lg p-4 mb-4">
            <h4 class="font-semibold text-blue-800 mb-2">🤖 Phân tích AI</h4>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p class="text-blue-700 font-medium">Entities:</p>
                <p class="text-blue-600">${g.entities.join(", ") || "Không có"}</p>
              </div>
              <div>
                <p class="text-blue-700 font-medium">Keywords:</p>
                <p class="text-blue-600">${g.keywords.join(", ") || "Không có"}</p>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>📄 ${g.claims.length} luận điểm</span>
              <span>🔗 ${g.sources.length} nguồn</span>
            </div>
            <div class="flex space-x-2">
              <button
                class="px-5 py-2 text-white text-sm font-medium rounded-lg
                      bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600
                      hover:from-blue-600 hover:to-purple-800
                      transition-all shadow-md"
                onclick="goToEditor(${g.group_id})">
                Phân tích kịch bản
              </button>
            </div>
          </div>
        </div>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    console.error("Error loading claims:", err);
    container.innerHTML =
      "<p class='text-red-600 p-6 bg-red-50 rounded-lg'>❌ Không thể tải dữ liệu AI nhóm.</p>";
  }
}

function goToEditor(groupId) {
  window.location.href = `editor_ai.html?group_id=${groupId}`;
}

async function openGroupDetail(groupId) {
  try {
    const res = await fetch("../backend/data/claims_grouped_summary.json");
    const groups = await res.json();
    const g = groups.find((x) => x.group_id === groupId);
    if (!g) return;

    const modal = document.getElementById("newsModal");
    const modalContent = document.getElementById("modalContent");
    modalContent.innerHTML = `
      <h2 class="text-2xl font-bold text-gray-800 mb-4">🧠 ${g.topic}</h2>
      <p class="text-gray-700 mb-4">${g.summary}</p>

      <div class="bg-blue-50 rounded-lg p-4 mb-4">
        <h4 class="font-semibold text-blue-800 mb-2">📄 Các tuyên bố</h4>
        <ul class="list-disc ml-6 text-gray-700">
          ${g.claims.map((c) => `<li>${c}</li>`).join("")}
        </ul>
      </div>

      <p><strong>🏷️ Thực thể:</strong> ${g.entities.join(", ") || "Không có"}</p>
      <p><strong>🔑 Từ khóa:</strong> ${g.keywords.join(", ") || "Không có"}</p>
      <p><strong>🔗 Nguồn:</strong> ${g.sources
        .map((u) => `<a href="${u}" target="_blank" class="text-blue-600 underline">${u}</a>`)
        .join(", ")}</p>
      <p class="mt-4"><strong>🧾 Độ tin cậy trung bình:</strong> ${
        g.avg_reliability || "N/A"
      }</p>
      <p><strong>⚖️ Mâu thuẫn:</strong> ${g.conflict ? "⚠️ Có mâu thuẫn" : "✅ Không có"}</p>
    `;
    modal.classList.remove("hidden");
  } catch (err) {
    console.error(err);
  }
}

// Close modal (reuse your existing function)
function closeNewsDetail() {
  document.getElementById("newsModal").classList.add("hidden");
}

window.addEventListener("DOMContentLoaded", loadClaimGroups);

async function loadTrendingTopics() {
    try {
        const res = await fetch("../backend/data/claims_grouped_summary.json");
        const data = await res.json();

        // Count topics
        const topicCount = {};
        data.forEach(item => {
            if (!topicCount[item.topic]) topicCount[item.topic] = 0;
            topicCount[item.topic]++;
        });

        // Convert to array & sort
        const topics = Object.entries(topicCount)
            .map(([topic, count]) => ({ topic, count }))
            .sort((a, b) => b.count - a.count);

        // Colors + icons (auto-cycle)
        const colors = ["red", "blue", "green", "yellow", "purple"];
        const icons = ["🔥", "📈", "🚦", "⭐", "📌"];

        const container = document.getElementById("trending-topic");
        container.innerHTML = "";

        topics.forEach((t, i) => {
            const color = colors[i % colors.length];
            const icon = icons[i % icons.length];

            container.innerHTML += `
                <div class="flex items-center justify-between p-3 bg-${color}-50 rounded-lg">
                    <div>
                        <p class="font-medium text-${color}-800">${t.topic}</p>
                        <p class="text-sm text-${color}-600">${t.count} nhóm chủ đề</p>
                    </div>
                    <span class="text-${color}-500 text-xl">${icon}</span>
                </div>
            `;
        });

    } catch (e) {
        console.error("Lỗi load trending topics:", e);
    }
}

loadTrendingTopics();

// ===============================
// 1. Load Claim Groups (Replace this with API fetch)
// ===============================

let claimGroups = [];
async function loadData() {
    const response = await fetch("../backend/data/claims_grouped_summary.json");
    claimGroups = await response.json();

    populateTopicDropdown();
    populateKeywordDropdown();
    renderResults(claimGroups);
}

loadData();


// ===============================
// 2. Extract Unique Topics
// ===============================

function populateTopicDropdown() {
    const select = document.getElementById("filterTopic");

    // Extract distinct topics
    const topics = [...new Set(claimGroups.map(c => c.topic).filter(Boolean))];

    topics.forEach(topic => {
        const option = document.createElement("option");
        option.value = topic;
        option.textContent = topic;
        select.appendChild(option);
    });
}


// ===============================
// 3. Extract Unique Keywords
// ===============================

function populateKeywordDropdown() {
    const select = document.getElementById("filterKeyword");

    // Flatten all keywords and dedupe
    const keywords = [
        ...new Set(
            claimGroups
                .flatMap(c => c.keywords || [])
                .filter(Boolean)
        )
    ];

    keywords.forEach(keyword => {
        const option = document.createElement("option");
        option.value = keyword;
        option.textContent = keyword;
        select.appendChild(option);
    });
}


// ===============================
// 4. Apply Filters
// ===============================

function applyFilters() {
    const titleQuery = document.getElementById("searchTitle").value.toLowerCase();
    const selectedTopic = document.getElementById("filterTopic").value;
    const selectedKeyword = document.getElementById("filterKeyword").value;

    let filtered = claimGroups;

    // Search by title
    if (titleQuery) {
        filtered = filtered.filter(c =>
            (c.summary || "").toLowerCase().includes(titleQuery)
        );
    }

    // Filter by topic
    if (selectedTopic) {
        filtered = filtered.filter(c => c.topic === selectedTopic);
    }

    // Filter by keyword
    if (selectedKeyword) {
        filtered = filtered.filter(c =>
            c.keywords && c.keywords.includes(selectedKeyword)
        );
    }

    renderResults(filtered);
}

document.getElementById("applyFilterBtn").addEventListener("click", applyFilters);


// ===============================
// 5. Render Results
// ===============================

function renderResults(data) {
  data = [...data].sort((a, b) => b.avg_reliability - a.avg_reliability);

    const container = document.querySelector(".lg\\:col-span-2");
    container.innerHTML = "";

    if (data.length === 0) {
        container.innerHTML = "<p class='text-gray-500 p-4'>Không tìm thấy kết quả.</p>";
        return;
    }

    data.forEach((g) => {
        const div = document.createElement("div");
        div.className =
        "bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer fade-in";

        div.innerHTML = `
            <div class="p-6">
              <div class="flex items-start justify-between mb-4">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-blue-600 rounded flex items-center justify-center">
                    <span class="text-white font-bold text-xs">${(g.topic || "?").slice(0, 2).toUpperCase()}</span>
                  </div>
                  <div>
                    <p class="font-medium text-gray-800">${g.topic || "Không rõ chủ đề"}</p>
                    <p class="text-sm text-gray-500">${g.sources.length} nguồn</p>
                  </div>
                </div>
                <div class="flex items-center space-x-2">
                  ${g.conflict
                    ? `<span class="bg-red-100 text-red-800 px-2.5 py-1.5 rounded-full text-xs font-medium">⚠️ Mâu thuẫn</span>`
                    : `<span class="bg-green-100 text-green-800 px-2.5 py-1.5 rounded-full text-xs font-medium">Không mâu thuẫn</span>`
                  }
                  <span class="bg-blue-100 text-blue-800 px-2.5 py-1.5 rounded-full text-xs font-medium">Độ tin cậy: ${(g.avg_reliability * 100).toFixed(0)}%</span>
                </div>
              </div>

              <h3 class="text-lg font-bold text-gray-800 mb-3 line-clamp-2">${g.summary}</h3>

              <p class="text-gray-600 mb-4 line-clamp-3">
                ${g.claims.slice(0, 3).join(" ")}${g.claims.length > 3 ? "..." : ""}
              </p>

              <div class="bg-blue-50 rounded-lg p-4 mb-4">
                <h4 class="font-semibold text-blue-800 mb-2">🤖 Phân tích AI</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p class="text-blue-700 font-medium">Entities:</p>
                    <p class="text-blue-600">${g.entities.join(", ") || "Không có"}</p>
                  </div>
                  <div>
                    <p class="text-blue-700 font-medium">Keywords:</p>
                    <p class="text-blue-600">${g.keywords.join(", ") || "Không có"}</p>
                  </div>
                </div>
              </div>
            </div>
        `;

        container.appendChild(div);
    });
}