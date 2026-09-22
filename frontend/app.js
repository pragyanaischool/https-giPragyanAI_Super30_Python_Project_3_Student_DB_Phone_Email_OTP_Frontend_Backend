// Automatically switches between local dev and live Render production endpoint
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000/api"
  : "https://student-verification-backend.onrender.com/api";

let currentPage = 1;
let deptChartInstance = null;
let verifyChartInstance = null;
let searchDebounceTimeout = null;
let activeStudent = { phone: "", email: "" };

// -------------------------------------------------------------
// Tab Switching Controller
// -------------------------------------------------------------
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(el => el.classList.remove("active"));

  const targetPane = document.getElementById(tabId);
  const targetBtn = document.getElementById(`btn-${tabId}`);

  if (targetPane) targetPane.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  if (tabId === "admin-tab") {
    loadAllAdminData();
  }
}

// -------------------------------------------------------------
// Analytics Data & Chart Visualizers
// -------------------------------------------------------------
async function loadAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/analytics`);
    if (!res.ok) throw new Error("Failed to load analytics");
    const data = await res.json();

    // 1. KPI Cards
    document.getElementById("kpi-total").innerText = Number(data.kpis.total_students || 0).toLocaleString();
    document.getElementById("kpi-verified").innerText = Number(data.kpis.fully_verified || 0).toLocaleString();
    document.getElementById("kpi-pending").innerText = Number(data.kpis.partially_verified || 0).toLocaleString();
    document.getElementById("kpi-rate").innerText = `${data.kpis.verification_rate || 0}%`;

    // 2. Bar Chart: Department Distribution
    const deptLabels = Object.keys(data.department_distribution || {});
    const deptValues = Object.values(data.department_distribution || {});

    if (deptChartInstance) deptChartInstance.destroy();
    const deptCtx = document.getElementById("deptChart").getContext("2d");
    deptChartInstance = new Chart(deptCtx, {
      type: "bar",
      data: {
        labels: deptLabels,
        datasets: [{
          label: "Enrolled Students",
          data: deptValues,
          backgroundColor: "#3b82f6",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#151d30",
            titleColor: "#f8fafc",
            bodyColor: "#94a3b8",
            borderColor: "#222f49",
            borderWidth: 1
          }
        },
        scales: {
          x: {
            ticks: { color: "#94a3b8", font: { size: 11 } },
            grid: { color: "#222f49" }
          },
          y: {
            ticks: { color: "#94a3b8", stepSize: 5 },
            grid: { color: "#222f49" }
          }
        }
      }
    });

    // 3. Doughnut Chart: Verification Breakdown
    const verifyLabels = Object.keys(data.verification_breakdown || {});
    const verifyValues = Object.values(data.verification_breakdown || {});

    if (verifyChartInstance) verifyChartInstance.destroy();
    const verifyCtx = document.getElementById("verifyChart").getContext("2d");
    verifyChartInstance = new Chart(verifyCtx, {
      type: "doughnut",
      data: {
        labels: verifyLabels,
        datasets: [{
          data: verifyValues,
          backgroundColor: ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", boxWidth: 12, padding: 12, font: { size: 11 } }
          }
        }
      }
    });

  } catch (err) {
    console.error("Analytics fetch error:", err);
  }
}

// -------------------------------------------------------------
// Paginated Student Directory Loader
// -------------------------------------------------------------
async function fetchTableData() {
  const search = document.getElementById("searchBox").value.trim();
  const department = document.getElementById("deptFilter").value;
  const statusFilter = document.getElementById("statusFilter").value;

  const params = new URLSearchParams({
    page: currentPage,
    limit: 10,
    search: search,
    department: department,
    status_filter: statusFilter
  });

  try {
    const res = await fetch(`${API_BASE}/students?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to load students");
    const result = await res.json();
    const tbody = document.getElementById("studentTableBody");
    tbody.innerHTML = "";

    if (!result.students || result.students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="color: #94a3b8;">No matching student records found.</td></tr>`;
      document.getElementById("pageInfo").innerText = "Showing Page 0 of 0 (0 records)";
      document.getElementById("prevBtn").disabled = true;
      document.getElementById("nextBtn").disabled = true;
      return;
    }

    result.students.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>#${s.id}</td>
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.email)}</td>
        <td>${escapeHtml(s.phone)}</td>
        <td>${escapeHtml(s.department)}</td>
        <td>Sem ${s.semester}</td>
        <td><span class="tag ${s.phone_verified ? 'ok' : 'no'}">${s.phone_verified ? '✓ Verified' : 'Pending'}</span></td>
        <td><span class="tag ${s.email_verified ? 'ok' : 'no'}">${s.email_verified ? '✓ Verified' : 'Pending'}</span></td>
      `;
      tbody.appendChild(tr);
    });

    const totalPages = result.total_pages || 1;
    document.getElementById("pageInfo").innerText = `Showing Page ${result.page} of ${totalPages} (${result.total} records)`;
    document.getElementById("prevBtn").disabled = result.page <= 1;
    document.getElementById("nextBtn").disabled = result.page >= totalPages;

  } catch (err) {
    console.error("Student list error:", err);
    document.getElementById("studentTableBody").innerHTML = `
      <tr><td colspan="8" class="text-center" style="color: #ef4444;">Error fetching data. Is the backend running?</td></tr>
    `;
  }
}

function debounceSearch() {
  clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    currentPage = 1;
    fetchTableData();
  }, 350);
}

function resetAndFetchTable() {
  currentPage = 1;
  fetchTableData();
}

function changePage(delta) {
  currentPage += delta;
  fetchTableData();
}

function loadAllAdminData() {
  loadAnalytics();
  fetchTableData();
}

// -------------------------------------------------------------
// Student Registration & OTP Flow
// -------------------------------------------------------------
async function handleRegistration(e) {
  e.preventDefault();
  const notify = document.getElementById("notifyMessage");
  const submitBtn = document.getElementById("submitRegBtn");

  const payload = {
    name: document.getElementById("stuName").value.trim(),
    email: document.getElementById("stuEmail").value.trim(),
    phone: document.getElementById("stuPhone").value.trim(),
    department: document.getElementById("stuDept").value,
    semester: parseInt(document.getElementById("stuSem").value, 10)
  };

  submitBtn.disabled = true;
  submitBtn.innerText = "Registering & Dispatching OTPs...";

  try {
    const res = await fetch(`${API_BASE}/students/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Registration failed");

    activeStudent.phone = payload.phone;
    activeStudent.email = payload.email;

    showNotification(notify, `${data.message} OTPs sent to ${payload.phone} and ${payload.email}`, "success");

    // Reveal OTP verification panel
    document.getElementById("otpDrawer").classList.remove("hidden");
    document.getElementById("phoneVerifyBadge").innerText = "";
    document.getElementById("emailVerifyBadge").innerText = "";
    document.getElementById("phoneOtpInput").disabled = false;
    document.getElementById("emailOtpInput").disabled = false;
    document.getElementById("btnVerifyPhone").disabled = false;
    document.getElementById("btnVerifyEmail").disabled = false;

  } catch (err) {
    showNotification(notify, err.message, "danger");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerText = "Register & Send OTPs";
  }
}

async function verifyOTP(type) {
  const notify = document.getElementById("notifyMessage");
  const identifier = type === "phone" ? activeStudent.phone : activeStudent.email;
  const inputId = type === "phone" ? "phoneOtpInput" : "emailOtpInput";
  const btnId = type === "phone" ? "btnVerifyPhone" : "btnVerifyEmail";
  const badgeId = type === "phone" ? "phoneVerifyBadge" : "emailVerifyBadge";

  const otp = document.getElementById(inputId).value.trim();

  if (!otp || otp.length < 4) {
    showNotification(notify, `Please enter a valid 6-digit ${type} OTP.`, "danger");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/students/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, otp, type })
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Verification failed");

    showNotification(notify, `✓ ${data.message}`, "success");

    // Disable input and update badge
    document.getElementById(inputId).disabled = true;
    document.getElementById(btnId).disabled = true;
    const badge = document.getElementById(badgeId);
    badge.innerText = "✓ Verified";
    badge.style.color = "#10b981";

    // Refresh directory if admin checks
    loadAnalytics();

  } catch (err) {
    showNotification(notify, err.message, "danger");
  }
}

// -------------------------------------------------------------
// Utilities
// -------------------------------------------------------------
function showNotification(el, message, type) {
  el.classList.remove("hidden");
  el.innerText = message;
  if (type === "success") {
    el.style.borderColor = "#10b981";
    el.style.background = "rgba(16, 185, 129, 0.15)";
    el.style.color = "#10b981";
  } else {
    el.style.borderColor = "#ef4444";
    el.style.background = "rgba(239, 68, 68, 0.15)";
    el.style.color = "#ef4444";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

// Initialize on load
window.addEventListener("DOMContentLoaded", () => {
  loadAllAdminData();
});
