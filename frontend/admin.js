const API_BASE = "http://127.0.0.1:8000";
const qs = (sel) => document.querySelector(sel);
const qsa = (sel) => document.querySelectorAll(sel);

function showAlert(msg, type = "info") {
  const existing = qs("#alertBox");
  if (existing) existing.remove();

  const div = document.createElement("div");
  div.id = "alertBox";
  div.className = `
    fixed top-5 right-5 z-50 px-4 py-2 rounded-lg shadow-md text-sm font-medium
    ${type === "error" ? "bg-red-100 text-red-700" :
      type === "success" ? "bg-green-100 text-green-700" :
      "bg-blue-100 text-blue-700"}
  `;
  div.textContent = msg;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), 3000);
}

// ====================================
// Navigation + Layout Controls
// ====================================

function setupNavigation() {
  const navItems = qsa(".nav-item");
  const pages = qsa(".page-content");
  const sidebarToggle = qs("#sidebarToggle");
  const sidebar = qs("#sidebar");
  const logoutBtn = qs("#logoutBtn");

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetPage = item.dataset.page;

      navItems.forEach(nav => {
        const icon = nav.querySelector("svg");
        if (nav === item) {
          nav.classList.add("bg-indigo-50", "text-indigo-600", "font-semibold");
          nav.classList.remove("text-gray-700");
          if (icon) icon.classList.add("text-indigo-600");
          if (icon) icon.classList.remove("text-gray-500");
        } else {
          nav.classList.remove("bg-indigo-50", "text-indigo-600", "font-semibold");
          nav.classList.add("text-gray-700");
          if (icon) icon.classList.remove("text-indigo-600");
          if (icon) icon.classList.add("text-gray-500");
        }
      });

      pages.forEach(page => {
        page.classList.toggle("hidden", page.id !== `${targetPage}Page`);
      });

      localStorage.setItem("activePage", targetPage);
    });
  });

  const savedPage = localStorage.getItem("activePage");
  if (savedPage) {
    const target = [...navItems].find(i => i.dataset.page === savedPage);
    if (target) target.click();
  } else {
    navItems[0]?.click();
  }

  sidebarToggle?.addEventListener("click", () =>
    sidebar.classList.toggle("-translate-x-full")
  );

  logoutBtn?.addEventListener("click", () => {
    if (confirm("Bạn có chắc chắn muốn đăng xuất?")) {
      showAlert("Đăng xuất thành công!", "success");
      window.location.href = "login.html";
    }
  });
}

// ====================================
// System Stats Simulation
// ====================================

function updateSystemStats() {
  const cpuBar = qs(".progress-bar");
  if (cpuBar) cpuBar.style.width = `${Math.floor(Math.random() * 30) + 50}%`;
}
setInterval(updateSystemStats, 30000);

// ====================================
// RSS Feed Management
// ====================================

function setupRssManagement() {
  const addRssBtn = qs("#addRssBtn");
  const addRssModal = qs("#addRssModal");
  const cancelRssBtn = qs("#cancelRssBtn");
  const rssForm = qs("#rssForm");
  const rssTableBody = qs("#rssTableBody");
  const rssFilter = qs("#rssFilter");

  // Modal
  addRssBtn?.addEventListener("click", () => addRssModal.classList.remove("hidden"));
  cancelRssBtn?.addEventListener("click", () => {
    addRssModal.classList.add("hidden");
    rssForm.reset();
  });

  async function loadRssList() {
    try {
      const res = await fetch(`${API_BASE}/rss/list`);
      if (!res.ok) throw new Error();
      const { rss = [] } = await res.json();
      renderRssTable(rss);
      renderRssFilter(rss);
    } catch {
      showAlert("⚠️ Không thể tải danh sách RSS.", "error");
    }
  }

  function renderRssFilter(rssList) {
    if (!rssFilter) return;
    const uniqueSources = [...new Set(rssList.map(r => r.source || "Không xác định"))];
    rssFilter.innerHTML = `<option value="all">Tất cả</option>` +
      uniqueSources.map(src => `<option value="${src}">${src}</option>`).join("");

    rssFilter.onchange = () => {
      const selected = rssFilter.value;
      const filtered = selected === "all" ? rssList : rssList.filter(r => r.source === selected);
      renderRssTable(filtered);
    };
  }

  function renderRssTable(rssList) {
    rssTableBody.innerHTML = rssList.map(rss => `
      <tr class="hover:bg-gray-50">
        <td class="py-4 px-4">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
              <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0z"/>
              </svg>
            </div>
            <span class="font-medium text-gray-900">${rss.source || "Không xác định"}</span>
          </div>
        </td>
        <td class="py-4 px-4 text-sm text-gray-600">${rss.url}</td>
        <td class="py-4 px-4">
          <button class="delete-rss text-red-600 hover:text-red-800 text-sm" data-url="${rss.url}">
            Xóa
          </button>
        </td>
      </tr>
    `).join("");
  }

  // Add RSS
  rssForm?.addEventListener("submit", async e => {
    e.preventDefault();
    const rssUrl = qs("#rssUrl").value.trim();
    if (!rssUrl) return showAlert("Vui lòng nhập URL RSS.", "error");
    try {
      const res = await fetch(`${API_BASE}/rss/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: rssUrl })
      });
      if (!res.ok) throw new Error();
      showAlert("✅ RSS nguồn đã được thêm!", "success");
      addRssModal.classList.add("hidden");
      rssForm.reset();
      await loadRssList();
    } catch {
      showAlert("⚠️ Lỗi khi thêm RSS!", "error");
    }
  });

  // Delete RSS
  document.addEventListener("click", async e => {
    if (e.target.classList.contains("delete-rss")) {
      const url = e.target.dataset.url;
      if (!confirm("Bạn có chắc muốn xóa RSS này?")) return;
      try {
        const res = await fetch(`${API_BASE}/rss/delete`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        if (!res.ok) throw new Error();
        showAlert("✅ Đã xóa RSS!", "success");
        await loadRssList();
      } catch {
        showAlert("⚠️ Lỗi khi xóa RSS!", "error");
      }
    }
  });

  loadRssList();
}

function setupYoutubeManagement() {
  const addBtn = qs("#addYoutubeBtn");
  const modal = qs("#addYoutubeModal");
  const cancelBtn = qs("#cancelYoutubeBtn");
  const form = qs("#youtubeForm");
  const tableBody = qs("#youtubeTableBody");
  const ytFilter = qs("#youtubeFilter"); // optional filter if you add it

  // ---- Modal handling ----
  addBtn?.addEventListener("click", () => modal.classList.remove("hidden"));
  cancelBtn?.addEventListener("click", () => {
    modal.classList.add("hidden");
    form.reset();
  });

  // ---- Load YouTube list ----
  async function loadYoutubeList() {
    try {
      const res = await fetch(`${API_BASE}/youtube/list`);
      if (!res.ok) throw new Error();
      const { youtube = [] } = await res.json();
      renderYoutubeTable(youtube);
      if (ytFilter) renderYoutubeFilter(youtube);
    } catch {
      showAlert("⚠️ Không thể tải danh sách YouTube.", "error");
    }
  }

  // ---- Optional filter ----
  function renderYoutubeFilter(list) {
    const uniqueDomains = [...new Set(list.map(i => i.domain || "Không xác định"))];

    ytFilter.innerHTML =
      `<option value="all">Tất cả</option>` +
      uniqueDomains.map(d => `<option value="${d}">${d}</option>`).join("");

    ytFilter.onchange = () => {
      const selected = ytFilter.value;
      const filtered =
        selected === "all" ? list : list.filter(i => i.domain === selected);
      renderYoutubeTable(filtered);
    };
  }

  // ---- Render table ----
  function renderYoutubeTable(list) {
    tableBody.innerHTML = list
      .map(
        item => `
      <tr class="hover:bg-gray-50">
        <td class="py-4 px-4 font-medium text-gray-800">${item.name}</td>
        <td class="py-4 px-4 text-sm text-blue-600">${item.url}</td>
        <td class="py-4 px-4">
          <button class="delete-youtube text-red-600 hover:text-red-800 text-sm"
                  data-url="${item.url}">
            Xóa
          </button>
        </td>
      </tr>
    `
      )
      .join("");
  }

  // ---- Add YouTube ----
  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const name = qs("#youtubeName").value.trim();
    const url = qs("#youtubeUrl").value.trim();

    if (!name || !url)
      return showAlert("Vui lòng nhập đầy đủ thông tin.", "error");

    try {
      const res = await fetch(`${API_BASE}/youtube/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url })
      });
      if (!res.ok) throw new Error();

      showAlert("✅ Đã thêm kênh YouTube!", "success");
      modal.classList.add("hidden");
      form.reset();
      await loadYoutubeList();
    } catch {
      showAlert("⚠️ Lỗi khi thêm kênh YouTube!", "error");
    }
  });

  // ---- Delete YouTube ----
  document.addEventListener("click", async e => {
    if (e.target.classList.contains("delete-youtube")) {
      const url = e.target.dataset.url;
      if (!confirm("Bạn có chắc muốn xóa kênh này?")) return;

      try {
        const res = await fetch(`${API_BASE}/youtube/delete`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        if (!res.ok) throw new Error();

        showAlert("✅ Đã xóa kênh!", "success");
        await loadYoutubeList();
      } catch {
        showAlert("⚠️ Lỗi khi xóa kênh!", "error");
      }
    }
  });

  loadYoutubeList();
}

// ====================================
// User Management
// ====================================

function setupUserManagement() {
  const apiBase = `${API_BASE}/users`;
  let isEditing = false, editingId = null;
  let currentPage = 1;
  const pageSize = 10;
  let totalUsers = 0;

  async function loadUsers(page = 1) {
    try {
      const skip = (page - 1) * pageSize;
      const res = await fetch(`${apiBase}?skip=${skip}&limit=${pageSize}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const users = data.users;
      totalUsers = data.total;

      const tbody = qs("#userTableBody");
      tbody.innerHTML = users.map(user => `
        <tr class="hover:bg-gray-50">
          <td class="py-4 px-4 flex items-center space-x-3">
            <div class="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center text-white">
              ${user.username.charAt(0).toUpperCase()}
            </div>
            <span class="font-medium text-gray-900">${user.username}</span>
          </td>
          <td class="py-4 px-4">
            <span class="bg-${user.role === "Admin" ? "red" : "green"}-100 text-${user.role === "Admin" ? "red" : "green"}-800 text-xs px-2 py-1 rounded-full">
              ${user.role}
            </span>
          </td>
          <td class="py-4 px-4 flex space-x-2">
            <button class="edit-user text-indigo-600" data-id="${user.id}" data-username="${user.username}" data-role="${user.role}">Sửa</button>
            <button class="delete-user text-red-600" data-id="${user.id}">Xóa</button>
          </td>
        </tr>
      `).join("");

      renderPagination(page);
    } catch {
      showAlert("⚠️ Không thể tải danh sách người dùng.", "error");
    }
  }

  async function updateUserStats() {
    try {
      const res = await fetch(`${apiBase}/stats`);
      if (!res.ok) throw new Error();
      const data = await res.json();

      document.querySelectorAll(".totalUsers").forEach(el => el.textContent = data.total);
      qs("#adminCount").textContent = data.admin;
      qs("#editorCount").textContent = data.editor;
    } catch (err) {
      console.error("⚠️ Failed to update user stats:", err);
    }
  }

  function renderPagination(page) {
    const totalPages = Math.ceil(totalUsers / pageSize);
    const paginationContainer = qs("#pagination");
    if (!paginationContainer) return;

    paginationContainer.innerHTML = `
      <div class="text-sm text-gray-700">
        Hiển thị <span class="font-medium">${(page - 1) * pageSize + 1}</span>
        đến <span class="font-medium">${Math.min(page * pageSize, totalUsers)}</span>
        của <span class="font-medium">${totalUsers}</span> kết quả
      </div>
      <div class="flex items-center space-x-2">
        <button class="page-btn px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100" data-page="${page - 1}" ${page === 1 ? "disabled class='opacity-50 cursor-not-allowed'" : ""}>Trước</button>
        ${Array.from({ length: totalPages }, (_, i) => `
          <button class="page-btn px-3 py-1 ${i + 1 === page ? "bg-indigo-600 text-white" : "border border-gray-300 hover:bg-gray-100"} rounded text-sm" data-page="${i + 1}">
            ${i + 1}
          </button>
        `).join("")}
        <button class="page-btn px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100" data-page="${page + 1}" ${page === totalPages ? "disabled class='opacity-50 cursor-not-allowed'" : ""}>Sau</button>
      </div>
    `;

    paginationContainer.querySelectorAll(".page-btn").forEach(btn => {
      btn.addEventListener("click", e => {
        const newPage = parseInt(e.target.dataset.page);
        if (!isNaN(newPage) && newPage >= 1 && newPage <= totalPages) {
          currentPage = newPage;
          loadUsers(currentPage);
        }
      });
    });
  }

  // Add / Edit
  qs("#addUserBtn").addEventListener("click", () => {
    qs("#userForm").classList.remove("hidden");
    qs("#userFormTitle").textContent = "Thêm Người Dùng Mới";
    qs("#submitUserBtn").textContent = "Thêm";
    qs("#userFormElement").reset();
    isEditing = false;
  });

  qs("#cancelUserBtn").addEventListener("click", () => {
    qs("#userForm").classList.add("hidden");
    qs("#userFormElement").reset();
  });

  qs("#userFormElement").addEventListener("submit", async e => {
    e.preventDefault();
    const username = qs("#username").value.trim();
    const password = qs("#password").value.trim();
    const role = qs("#userRole").value;
    if (!username || (!password && !isEditing)) return showAlert("Điền đầy đủ thông tin!", "error");

    try {
      const res = await fetch(isEditing ? `${apiBase}/${editingId}` : apiBase, {
        method: isEditing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role })
      });
      if (!res.ok) throw new Error();
      showAlert(isEditing ? "Cập nhật thành công!" : "Thêm người dùng thành công!", "success");
      qs("#userForm").classList.add("hidden");
      await loadUsers();
      await updateUserStats();
    } catch {
      showAlert("⚠️ Lỗi khi lưu!", "error");
    }
  });

  // Edit / Delete
  document.addEventListener("click", async e => {
    if (e.target.classList.contains("edit-user")) {
      const { id, username, role } = e.target.dataset;
      qs("#username").value = username;
      qs("#userRole").value = role;
      qs("#userForm").classList.remove("hidden");
      qs("#userFormTitle").textContent = "Chỉnh Sửa Người Dùng";
      isEditing = true;
      editingId = id;
    }
    if (e.target.classList.contains("delete-user")) {
      const id = e.target.dataset.id;
      if (!confirm("Xóa người dùng này?")) return;
      await fetch(`${apiBase}/${id}`, { method: "DELETE" });
      await loadUsers();
      await updateUserStats();
    }
  });

  loadUsers();
  updateUserStats();
}

// Call this after a new user is added
async function addUser(newUserData) {
  const res = await fetch(`${API_BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newUserData)
  });

  if (res.ok) {
    await updateUserStats();
  }
}

// ===========================
// 🧭 Crawler Dashboard Logic
// ===========================

document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "http://127.0.0.1:8000";

    const runBtn = document.getElementById("runCrawlBtn");
    const logTableBody = document.getElementById("logTableBody");

    const totalTodayEl = document.querySelectorAll(".totalToday");
    const totalArticlesEl = document.getElementById("totalArticles");
    const successEl = document.querySelector(".text-2xl.font-bold.text-green-600");
    const failEl = document.querySelector(".text-2xl.font-bold.text-red-600");
    const successRateEl = document.querySelectorAll(".successRate");

    async function loadTotalArticles() {
      try {
        const res = await fetch(`${API_BASE}/system/total`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Không thể lấy dữ liệu tổng bài viết");

        updateStat(totalArticlesEl, data.total);
      } catch (err) {
        console.error("❌ Lỗi khi tải tổng bài viết:", err);
      }
    }


    // --- Helper: smooth stat updates ---
    function updateStat(el, newValue, highlight = true) {
        if (highlight) {
            el.classList.add("text-green-600", "transition", "duration-300");
            el.textContent = newValue.toLocaleString("vi-VN");
            setTimeout(() => el.classList.remove("text-green-600"), 800);
        } else {
            el.textContent = newValue.toLocaleString("vi-VN");
        }
    }

    let allResults = [];
    // --- Fetch logs and update UI ---
    async function loadLogs() {
        try {
            const res = await fetch(`${API_BASE}/crawler/logs`);
            const data = await res.json();

            if (!data.logs?.length) {
                logTableBody.innerHTML = `
                    <tr><td colspan="6" class="text-center py-6 text-gray-500">
                        Không có log nào được ghi nhận
                    </td></tr>`;
                updateStat(totalTodayEl, 0, false);
                updateStat(successEl, 0, false);
                updateStat(failEl, 0, false);
                successRateEl.textContent = "0.0%";
                return;
            }

            const today = new Date().toISOString().split("T")[0];
            let totalAddedToday = 0, totalSuccess = 0, totalFailed = 0;
            allResults = [];

            data.logs.forEach(session => {
              const sessionDate = session.time.split(" ")[0];

              const sessionAdded = (session.results || []).reduce((sum, r) => sum + (r.added || 0), 0);
                if (sessionDate === today) {
                    totalAddedToday += sessionAdded;
                }

                (session.results || []).forEach(r => {
                    const src = (r.source || "").toLowerCase();
                    let sourceId = "other";
                    let sourceName = r.source || "";

                    if (src.includes("vnexpress")) {
                        sourceId = "vnexpress"; sourceName = "VnExpress";
                    } else if (src.includes("tuoitre") || src.includes("tuoi-tre")) {
                        sourceId = "tuoitre"; sourceName = "Tuổi Trẻ";
                    } else if (src.includes("thanhnien")) {
                        sourceId = "thanhnien"; sourceName = "Thanh Niên";
                    } else {
                        // if r.source is already a friendly name, try to normalize it
                        const s = (r.source || "").toString();
                        if (s.toLowerCase().includes("vnexpress")) { sourceId = "vnexpress"; sourceName = "VnExpress"; }
                        else if (s.toLowerCase().includes("tuoi")) { sourceId = "tuoitre"; sourceName = "Tuổi Trẻ"; }
                        else if (s.toLowerCase().includes("thanh")) { sourceId = "thanhnien"; sourceName = "Thanh Niên"; }
                    }

                    allResults.push({
                        // keep original time string, but also add a date-only field for filtering
                        time: session.time,
                        date: sessionDate,          // YYYY-MM-DD
                        sourceId,                   // vnexpress | tuoitre | thanhnien | other
                        source: sourceName,         // friendly name for display
                        added: r.added || 0,
                        failed: r.failed || 0,
                        status: r.status || "unknown"
                    });

                    totalSuccess += (r.added || 0);
                    totalFailed += (r.failed || 0);
                });
            });

            // --- Update stats dynamically ---
            totalTodayEl.forEach(el => updateStat(el, totalAddedToday));
            updateStat(successEl, totalSuccess, false);
            updateStat(failEl, totalFailed, false);
            const totalOps = totalSuccess + totalFailed;
            const rate = totalOps > 0 ? (totalSuccess / totalOps * 100).toFixed(1) : "0.0";
            successRateEl.forEach(el => el.textContent = `${rate}%`);

            renderPaginatedLogs(allResults);

        } catch (err) {
            console.error("❌ Lỗi khi tải log:", err);
            logTableBody.innerHTML = `
                <tr><td colspan="6" class="text-center py-6 text-red-500">
                    Lỗi khi tải dữ liệu log
                </td></tr>`;
        }
    }

    function renderLogs(filteredLogs) {
      logTableBody.innerHTML = filteredLogs.map(log => {
          let color, label;
          switch (log.status) {
              case "success": color = "green"; label = "Thành công"; break;
              case "warning": color = "yellow"; label = "Cảnh báo"; break;
              case "empty": color = "gray"; label = "Không có dữ liệu"; break;
              default: color = "red"; label = "Thất bại";
          }

          const iconColor = {
              "vnexpress": "orange",
              "tuoitre": "blue",
              "thanhnien": "red"
          }[log.source.toLowerCase()] || "gray";

          const sourceName = log.source.includes("vnexpress")
              ? "VnExpress"
              : log.source.includes("tuoitre")
              ? "Tuổi Trẻ"
              : log.source.includes("thanhnien")
              ? "Thanh Niên"
              : log.source;

          return `
              <tr class="hover:bg-gray-50 transition">
                  <td class="py-4 px-4 text-sm text-gray-900">${log.time}</td>
                  <td class="py-4 px-4">
                      <div class="flex items-center space-x-2">
                          <div class="w-6 h-6 bg-${iconColor}-100 rounded flex items-center justify-center">
                              <svg class="w-3 h-3 text-${iconColor}-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                      d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z"></path>
                              </svg>
                          </div>
                          <span class="text-sm font-medium text-gray-900">${sourceName}</span>
                      </div>
                  </td>
                  <td class="py-4 px-4 text-sm text-green-600 font-medium">${log.added}</td>
                  <td class="py-4 px-4 text-sm text-red-600 font-medium">${log.failed}</td>
                  <td class="py-4 px-4">
                      <span class="bg-${color}-100 text-${color}-800 text-xs px-2 py-1 rounded-full">${label}</span>
                  </td>
              </tr>`;
      }).join("");

      if (filteredLogs.length === 0) {
          logTableBody.innerHTML = `
              <tr><td colspan="6" class="text-center py-6 text-gray-500">
                  Không có log nào khớp với bộ lọc
              </td></tr>`;
      }
  }

  /* ---------------------------
   Pagination setup
--------------------------- */
let currentPage = 1;
const logsPerPage = 10;

// Elements for pagination UI (update IDs to match your HTML)
const paginationInfo = document.getElementById("paginationInfo");
const paginationContainer = document.getElementById("paginationContainer");

function renderPaginatedLogs(data) {
  const totalLogs = data.length;
  const totalPages = Math.ceil(totalLogs / logsPerPage);

  // Clamp currentPage to valid range
  if (currentPage > totalPages) currentPage = totalPages || 1;

  const startIdx = (currentPage - 1) * logsPerPage;
  const endIdx = startIdx + logsPerPage;
  const visibleLogs = data.slice(startIdx, endIdx);

  // Render table rows
  renderLogs(visibleLogs);

  // Update info text
  const from = totalLogs === 0 ? 0 : startIdx + 1;
  const to = Math.min(endIdx, totalLogs);
  paginationInfo.innerHTML = `
    Hiển thị <span class="font-medium">${from}</span> đến 
    <span class="font-medium">${to}</span> của 
    <span class="font-medium">${totalLogs}</span> log
  `;

  // Rebuild page buttons
  renderPaginationControls(totalPages, data);
}

function renderPaginationControls(totalPages, data) {
  paginationContainer.innerHTML = "";

  // --- Previous Button ---
  const prevBtn = document.createElement("button");
  prevBtn.textContent = "Trước";
  prevBtn.className =
    "px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100";
  if (currentPage === 1) prevBtn.disabled = true;
  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderPaginatedLogs(data);
    }
  });
  paginationContainer.appendChild(prevBtn);

  // --- Page Number Buttons ---
  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;
    btn.className =
      "px-3 py-1 rounded text-sm " +
      (i === currentPage
        ? "bg-indigo-600 text-white"
        : "border border-gray-300 hover:bg-gray-100");
    btn.addEventListener("click", () => {
      currentPage = i;
      renderPaginatedLogs(data);
    });
    paginationContainer.appendChild(btn);
  }

  // --- Next Button ---
  const nextBtn = document.createElement("button");
  nextBtn.textContent = "Sau";
  nextBtn.className =
    "px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100";
  if (currentPage === totalPages || totalPages === 0) nextBtn.disabled = true;
  nextBtn.addEventListener("click", () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderPaginatedLogs(data);
    }
  });
  paginationContainer.appendChild(nextBtn);
}


  function normalizeText(str) {
      return str
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase();
  }

async function loadSources() {
  try {
    const res = await fetch(`${API_BASE}/rss/list`);
    const data = await res.json();

    const sourceSelect = document.getElementById("sourceFilter");
    sourceSelect.innerHTML = `<option value="">Tất cả nguồn</option>`;

    (data.rss || []).forEach(item => {
      try {
        const urlObj = new URL(item.url);
        const domain = urlObj.hostname.replace("www.", "");
        // Label shows full URL like https://vnexpress.net/rss/thoi-su.rss
        sourceSelect.innerHTML += `<option value="${domain}">${item.url}</option>`;
      } catch {
        // fallback for malformed URL
        sourceSelect.innerHTML += `<option value="${item.url}">${item.url}</option>`;
      }
    });
  } catch (err) {
    console.error("❌ Lỗi khi tải danh sách RSS:", err);
  }
}

function extractDomain(str) {
  try {
    return new URL(str).hostname.replace("www.", "");
  } catch {
    return str; // fallback if not a full URL
  }
}

  document.getElementById("filterLogsBtn").addEventListener("click", () => {
      const fromDate = document.getElementById("fromDate").value;
      const toDate = document.getElementById("toDate").value;
      const sourceFilter = document.getElementById("sourceFilter").value; 

      let filtered = allResults.slice();

      // --- Date filter (inclusive) ---
      if (fromDate) {
          filtered = filtered.filter(log => log.date >= fromDate);
      }
      if (toDate) {
          filtered = filtered.filter(log => log.date <= toDate);
      }

      if (sourceFilter) {
        filtered = filtered.filter(log => {
          const logDomain = extractDomain(log.source);
          return normalizeText(logDomain).includes(normalizeText(sourceFilter));
        });
      }
    currentPage = 1;
    renderPaginatedLogs(filtered);
  });

  loadSources();

    // --- Run crawler manually ---
    runBtn.addEventListener("click", async () => {
        runBtn.disabled = true;
        runBtn.innerHTML = `
            <svg class="animate-spin w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
            </svg> Đang chạy...`;

        try {
            const res = await fetch(`${API_BASE}/crawler/run`, { method: "POST" });
            const data = await res.json();

            if (!res.ok || data.error) {
                alert(`❌ Lỗi khi crawl: ${data.error || "Không xác định"}`);
                return;
            }

            const message = data.message ?? `Crawl completed! (${data.log?.total_new ?? 0} bài viết mới)`;
            alert(`✅ ${message}`);

            await loadLogs();
        } catch (err) {
            alert("❌ Lỗi khi gọi API: " + err.message);
        } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582A10.97 10.97 0 0012 4c6.075 0 11 4.925 11 11h-2a9 9 0 10-9 9c4.97 0 9-4.03 9-9h2c0 6.075-4.925 11-11 11S1 17.075 1 11H4z"/>
                </svg> <span>Chạy Crawl Ngay</span>`;
        }
    });

    // --- Initial load ---
    loadSources();
    loadLogs();
    loadTotalArticles();
});

async function updateSystemStats() {
  try {
    const res = await fetch(`${API_BASE}/system/status`);
    const data = await res.json();

    // --- CPU ---
    document.getElementById("cpuValue").textContent = `${data.cpu}%`;
    document.getElementById("cpuBar").style.width = `${data.cpu}%`;

    // --- Memory ---
    document.getElementById("memoryValue").textContent = `${data.memory}%`;
    document.getElementById("memoryBar").style.width = `${data.memory}%`;

    // --- Storage ---
    document.getElementById("storageValue").textContent = `${data.storage.toFixed(1)}%`;
    document.getElementById("storageBar").style.width = `${data.storage}%`;

    // --- Service statuses ---
    function setStatus(el, ok) {
      el.textContent = ok ? "● Online" : "● Offline";
      el.className = ok
        ? "text-sm font-medium text-green-600"
        : "text-sm font-medium text-red-600";
    }

    setStatus(document.getElementById("dbStatus"), data.services.database);
    setStatus(document.getElementById("apiStatus"), data.services.api);
    setStatus(document.getElementById("queueStatus"), data.services.queue);
  } catch (err) {
    console.error("❌ Lỗi khi tải trạng thái hệ thống:", err);
  }
}

// Run once and refresh every 10 seconds
updateSystemStats();
setInterval(updateSystemStats, 10000);

// ====================================
// Initialize Everything
// ====================================

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupRssManagement();
  setupUserManagement();
  setupYoutubeManagement();
  updateSystemStats();
});
