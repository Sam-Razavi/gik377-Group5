const API_BASE_URL = "http://127.0.0.1:8000";

let accessToken = localStorage.getItem("accessToken") || null;
let currentOrderRef = null;
let bankIdPollingInterval = null;

function setOutput(data) {
  document.getElementById("output").textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function showMessage(message, type = "info") {
  const box = document.getElementById("message-box");

  box.classList.remove("hidden");
  box.className = "mb-6 rounded-2xl border px-4 py-3 text-sm";

  if (type === "success") {
    box.classList.add(
      "bg-emerald-500/15",
      "border-emerald-400/30",
      "text-emerald-200"
    );
  } else if (type === "error") {
    box.classList.add(
      "bg-red-500/15",
      "border-red-400/30",
      "text-red-200"
    );
  } else {
    box.classList.add(
      "bg-blue-500/15",
      "border-blue-400/30",
      "text-blue-200"
    );
  }

  box.textContent = message;
}

function clearMessage() {
  const box = document.getElementById("message-box");
  box.classList.add("hidden");
  box.textContent = "";
}

function updateTokenStatus() {
  document.getElementById("token-status").textContent = accessToken
    ? "Token stored"
    : "No token yet";
}

function updateOrderRefStatus() {
  document.getElementById("order-ref-status").textContent =
    currentOrderRef || "None";
}

function updatePollingStatus(isPolling) {
  document.getElementById("polling-status").textContent = isPolling
    ? "Running"
    : "Stopped";
}

function updateBankIdLiveStatus(text, classes = []) {
  const badge = document.getElementById("bankid-live-status");
  badge.textContent = text;
  badge.className = "text-xs px-3 py-1 rounded-full";

  if (classes.length) {
    badge.classList.add(...classes);
  } else {
    badge.classList.add("bg-white/10", "text-slate-200");
  }
}

function clearOutput() {
  setOutput("");
  clearMessage();
}

function setButtonLoading(buttonId, isLoading, loadingText) {
  const button = document.getElementById(buttonId);
  if (!button) return;

  if (isLoading) {
    button.disabled = true;
    button.classList.add("opacity-70", "cursor-not-allowed");
    button.innerHTML = `
      <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
      </svg>
      <span>${loadingText}</span>
    `;
  } else {
    button.disabled = false;
    button.classList.remove("opacity-70", "cursor-not-allowed");

    const labels = {
      "register-btn": "Register",
      "login-btn": "Login",
      "me-btn": "Get /auth/me",
      "bankid-initiate-btn": "Initiate BankID",
      "bankid-status-btn": "Check BankID Status",
    };

    button.innerHTML = `<span>${labels[buttonId] || "Submit"}</span>`;
  }
}

function logoutUser() {
  accessToken = null;
  localStorage.removeItem("accessToken");
  updateTokenStatus();
  showMessage("Logged out successfully.", "success");
  setOutput({ message: "Token removed from localStorage." });
}

async function registerUser() {
  clearMessage();

  const full_name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  if (!full_name || !email || !password) {
    showMessage("Please fill in all register fields.", "error");
    return;
  }

  setButtonLoading("register-btn", true, "Registering...");

  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ full_name, email, password }),
    });

    const data = await response.json();
    setOutput(data);

    if (response.ok) {
      showMessage("User registered successfully.", "success");
    } else {
      showMessage(data.detail || "Registration failed.", "error");
    }
  } catch (error) {
    showMessage(`Network error: ${error.message}`, "error");
    setOutput({ error: error.message });
  } finally {
    setButtonLoading("register-btn", false);
  }
}

async function loginUser() {
  clearMessage();

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    showMessage("Please fill in email and password.", "error");
    return;
  }

  setButtonLoading("login-btn", true, "Logging in...");

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    setOutput(data);

    if (response.ok && data.access_token) {
      accessToken = data.access_token;
      localStorage.setItem("accessToken", accessToken);
      updateTokenStatus();
      showMessage("Login successful. Token stored.", "success");
    } else {
      showMessage(data.detail || "Login failed.", "error");
    }
  } catch (error) {
    showMessage(`Network error: ${error.message}`, "error");
    setOutput({ error: error.message });
  } finally {
    setButtonLoading("login-btn", false);
  }
}

async function getCurrentUser() {
  clearMessage();

  if (!accessToken) {
    showMessage("No token available. Please log in first.", "error");
    return;
  }

  setButtonLoading("me-btn", true, "Fetching user...");

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    const data = await response.json();
    setOutput(data);

    if (response.ok) {
      showMessage("Fetched current user successfully.", "success");
    } else {
      showMessage(data.detail || "Could not fetch current user.", "error");
    }
  } catch (error) {
    showMessage(`Network error: ${error.message}`, "error");
    setOutput({ error: error.message });
  } finally {
    setButtonLoading("me-btn", false);
  }
}

async function startBankID() {
  clearMessage();
  setButtonLoading("bankid-initiate-btn", true, "Starting BankID...");
  updateBankIdLiveStatus("Starting...", ["bg-sky-500/20", "text-sky-200"]);

  try {
    const response = await fetch(`${API_BASE_URL}/auth/bankid/initiate`, {
      method: "POST",
    });

    const data = await response.json();
    setOutput(data);

    if (response.ok && data.orderRef) {
      currentOrderRef = data.orderRef;
      updateOrderRefStatus();

      showMessage(
        "BankID initiated successfully. Opening BankID app...",
        "success"
      );

      if (data.autoStartToken) {
        const bankIdUrl = `bankid:///?autostarttoken=${encodeURIComponent(
          data.autoStartToken
        )}&redirect=null`;

        window.location.href = bankIdUrl;
      }

      startBankIDPolling();
    } else {
      updateBankIdLiveStatus("Error", ["bg-red-500/20", "text-red-200"]);
      showMessage(
        data.detail || data.details || "Could not initiate BankID.",
        "error"
      );
    }
  } catch (error) {
    updateBankIdLiveStatus("Error", ["bg-red-500/20", "text-red-200"]);
    showMessage(`Network error: ${error.message}`, "error");
    setOutput({ error: error.message });
  } finally {
    setButtonLoading("bankid-initiate-btn", false);
  }
}

async function checkBankIDStatus() {
  if (!currentOrderRef) {
    showMessage("No orderRef available. Start BankID first.", "error");
    return;
  }

  setButtonLoading("bankid-status-btn", true, "Checking status...");

  try {
    const response = await fetch(
      `${API_BASE_URL}/auth/bankid/status/${currentOrderRef}`,
      {
        method: "GET",
      }
    );

    const data = await response.json();
    setOutput(data);

    if (response.ok && data.access_token) {
      accessToken = data.access_token;
      localStorage.setItem("accessToken", accessToken);
      updateTokenStatus();
      updateBankIdLiveStatus("Complete", [
        "bg-emerald-500/20",
        "text-emerald-200",
      ]);
      showMessage(
        "BankID login completed successfully. You are now logged in.",
        "success"
      );
      stopBankIDPolling();
      await getCurrentUser();
    } else if (response.ok) {
      const status = data.status || "unknown";

      if (status === "pending") {
        updateBankIdLiveStatus("Pending", [
          "bg-amber-500/20",
          "text-amber-200",
        ]);
      } else if (status === "failed") {
        updateBankIdLiveStatus("Failed", ["bg-red-500/20", "text-red-200"]);
        stopBankIDPolling();
      } else {
        updateBankIdLiveStatus(status, ["bg-white/10", "text-slate-200"]);
      }

      showMessage(`BankID status: ${status}`, "info");
    } else {
      updateBankIdLiveStatus("Error", ["bg-red-500/20", "text-red-200"]);
      showMessage(data.detail || "Could not fetch BankID status.", "error");
    }
  } catch (error) {
    updateBankIdLiveStatus("Error", ["bg-red-500/20", "text-red-200"]);
    showMessage(`Network error: ${error.message}`, "error");
    setOutput({ error: error.message });
  } finally {
    setButtonLoading("bankid-status-btn", false);
  }
}

function startBankIDPolling() {
  stopBankIDPolling();
  updatePollingStatus(true);
  updateBankIdLiveStatus("Polling...", ["bg-violet-500/20", "text-violet-200"]);

  bankIdPollingInterval = setInterval(() => {
    checkBankIDStatus();
  }, 2000);
}

function stopBankIDPolling() {
  if (bankIdPollingInterval) {
    clearInterval(bankIdPollingInterval);
    bankIdPollingInterval = null;
  }

  updatePollingStatus(false);

  if (
    document.getElementById("bankid-live-status").textContent === "Polling..."
  ) {
    updateBankIdLiveStatus("Stopped", ["bg-white/10", "text-slate-200"]);
  }
}

updateTokenStatus();
updateOrderRefStatus();
updatePollingStatus(false);
updateBankIdLiveStatus("Idle", ["bg-white/10", "text-slate-200"]);