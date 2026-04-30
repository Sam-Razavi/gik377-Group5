let accessToken = localStorage.getItem("accessToken") || "";
let tempToken = localStorage.getItem("tempToken") || "";

let bankIdPollTimer = null;
let bankIdPollAttempts = 0;

const BANKID_POLL_INTERVAL_MS = 2000;
const BANKID_MAX_POLL_ATTEMPTS = 90;

document.addEventListener("DOMContentLoaded", () => {
  updateTokenBoxes();
  setStatus("Ready. Start with Health check.", "info");
});

function apiBase() {
  return document.getElementById("apiBase").value.replace(/\/$/, "");
}

function show(data) {
  document.getElementById("output").textContent = JSON.stringify(data, null, 2);
}

function clearOutput() {
  document.getElementById("output").textContent = "Ready.";
  setStatus("Output cleared.", "info");
}

function setStatus(message, type = "info") {
  const statusBox = document.getElementById("statusBox");

  if (!statusBox) return;

  statusBox.className = "status-box";

  if (type !== "info") {
    statusBox.classList.add(type);
  }

  statusBox.textContent = message;
}

function getErrorMessage(result) {
  if (!result) {
    return "Unknown error.";
  }

  if (result.data?.detail) {
    return result.data.detail;
  }

  if (result.data?.message) {
    return result.data.message;
  }

  if (result.status === 0) {
    return "Could not connect to backend. Make sure FastAPI is running.";
  }

  if (result.status === 400) {
    return "Bad request. Check the form values.";
  }

  if (result.status === 401) {
    return "Unauthorized. Login again or check your token.";
  }

  if (result.status === 403) {
    return "Forbidden. You do not have access.";
  }

  if (result.status === 404) {
    return "Endpoint not found. Check the URL.";
  }

  if (result.status >= 500) {
    return "Server error. Check the backend terminal.";
  }

  return "Something went wrong.";
}

function updateTokenBoxes() {
  document.getElementById("accessTokenBox").textContent =
    accessToken || "No access token yet";

  document.getElementById("tempTokenBox").textContent =
    tempToken || "No temporary token yet";
}

function saveAccessToken(token) {
  accessToken = token || "";

  if (accessToken) {
    localStorage.setItem("accessToken", accessToken);
  }

  updateTokenBoxes();
}

function saveTempToken(token) {
  tempToken = token || "";

  if (tempToken) {
    localStorage.setItem("tempToken", tempToken);
  }

  updateTokenBoxes();
}

function clearTokens() {
  accessToken = "";
  tempToken = "";

  localStorage.removeItem("accessToken");
  localStorage.removeItem("tempToken");

  updateTokenBoxes();

  setStatus("Logged out. Login again to continue.", "info");

  show({
    message: "Logged out",
  });
}

async function request(path, options = {}) {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    const response = await fetch(`${apiBase()}${path}`, {
      ...options,
      headers,
    });

    const text = await response.text();

    let data;

    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = {
        raw: text,
      };
    }

    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: {
        detail:
          "Could not connect to backend. Make sure FastAPI is running on http://127.0.0.1:8000.",
        error: error.message,
      },
    };
  }
}

async function healthCheck() {
  setStatus("Checking backend connection...", "loading");

  const result = await request("/health");

  if (!result.ok) {
    setStatus(`Health check failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  setStatus("Backend is running.", "success");
  show(result);
}

async function registerUser() {
  setStatus("Registering user...", "loading");

  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const fullName = document.getElementById("registerName").value.trim();
  const homeAddress = document.getElementById("homeAddress").value.trim();
  const homeLat = document.getElementById("homeLat").value;
  const homeLon = document.getElementById("homeLon").value;

  if (!email || !password || !fullName) {
    setStatus("Please fill in email, password and full name.", "warning");
    return;
  }

  const body = {
    email,
    password,
    full_name: fullName,
    home_address: homeAddress || null,
    home_lat: homeLat ? parseFloat(homeLat) : null,
    home_lon: homeLon ? parseFloat(homeLon) : null,
  };

  const result = await request("/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!result.ok) {
    setStatus(`Registration failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  document.getElementById("loginEmail").value = email;
  document.getElementById("loginPassword").value = password;

  setStatus("User registered successfully. You can now login.", "success");
  show(result);
}

async function loginUser() {
  setStatus("Logging in...", "loading");

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!email || !password) {
    setStatus("Please enter both email and password.", "warning");
    return;
  }

  const result = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });

  if (!result.ok) {
    setStatus(`Login failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  if (result.data.requires_2fa && result.data.temp_token) {
    saveTempToken(result.data.temp_token);
    setStatus(
      "Password is correct. 2FA is required. Enter the code from your authenticator app.",
      "warning"
    );
    show(result);
    return;
  }

  if (result.data.access_token) {
    saveAccessToken(result.data.access_token);
    setStatus("Login successful. Access token saved.", "success");
  } else {
    setStatus("Login worked, but no access token was returned.", "warning");
  }

  show(result);
}

async function getMe() {
  setStatus("Fetching current user...", "loading");

  if (!accessToken) {
    setStatus("No access token found. Login first.", "warning");
    return;
  }

  const result = await request("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!result.ok) {
    setStatus(`Could not fetch current user: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  setStatus("Current user loaded successfully.", "success");
  show(result);
}

async function setup2FA() {
  setStatus("Setting up 2FA...", "loading");

  if (!accessToken) {
    setStatus("You must login before setting up 2FA.", "warning");
    return;
  }

  const result = await request("/auth/2fa/setup", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!result.ok) {
    setStatus(`2FA setup failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  const secret = result.data.secret;
  const provisioningUri = result.data.provisioning_uri;

  if (secret) {
    document.getElementById("twoFaSecret").value = secret;
  }

  const qrWrapper = document.getElementById("twoFaQrWrapper");
  const qrImage = document.getElementById("twoFaQrImage");
  const qrUrlBox = document.getElementById("twoFaQrUrl");

  if (!qrWrapper || !qrImage || !qrUrlBox) {
    setStatus("2FA setup worked, but QR elements are missing in HTML.", "error");
    show({
      error: "QR HTML elements are missing",
      fix: "Make sure auth-test.html contains twoFaQrWrapper, twoFaQrImage and twoFaQrUrl.",
      setupResponse: result,
    });
    return;
  }

  if (provisioningUri) {
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=190x190&data=${encodeURIComponent(
      provisioningUri
    )}`;

    qrImage.src = qrUrl;
    qrUrlBox.textContent = qrUrl;
    qrWrapper.classList.remove("hidden");

    setStatus(
      "2FA setup created. Scan the QR code, then enter the 6-digit code and click Enable 2FA.",
      "success"
    );
  } else {
    qrImage.removeAttribute("src");
    qrUrlBox.textContent = "No provisioning_uri found in backend response.";
    qrWrapper.classList.add("hidden");

    setStatus(
      "2FA setup worked, but no QR URI was returned. Use the secret manually.",
      "warning"
    );
  }

  show(result);
}

async function enable2FA() {
  setStatus("Enabling 2FA...", "loading");

  if (!accessToken) {
    setStatus("You must login before enabling 2FA.", "warning");
    return;
  }

  const code = document.getElementById("twoFaCode").value.trim();

  if (!code) {
    setStatus("Please enter the 6-digit code from your authenticator app.", "warning");
    return;
  }

  const result = await request("/auth/2fa/enable", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      code,
    }),
  });

  if (!result.ok) {
    setStatus(`Could not enable 2FA: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  setStatus("2FA enabled successfully. Next login will require a 2FA code.", "success");
  show(result);
}

async function disable2FA() {
  setStatus("Disabling 2FA...", "loading");

  if (!accessToken) {
    setStatus("You must login before disabling 2FA.", "warning");
    return;
  }

  const code = document.getElementById("twoFaCode").value.trim();

  if (!code) {
    setStatus("Please enter the current 6-digit code to disable 2FA.", "warning");
    return;
  }

  const result = await request("/auth/2fa/disable", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      code,
    }),
  });

  if (!result.ok) {
    setStatus(`Could not disable 2FA: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  setStatus("2FA disabled successfully.", "success");
  show(result);
}

async function complete2FALogin() {
  setStatus("Completing 2FA login...", "loading");

  const code = document.getElementById("loginTwoFaCode").value.trim();

  if (!tempToken) {
    setStatus("No temporary 2FA token found. Login again first.", "warning");
    return;
  }

  if (!code) {
    setStatus("Please enter the 6-digit 2FA code.", "warning");
    return;
  }

  const result = await request("/auth/login/2fa", {
    method: "POST",
    body: JSON.stringify({
      temp_token: tempToken,
      code,
    }),
  });

  if (!result.ok) {
    setStatus(`2FA login failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  if (result.data.access_token) {
    saveAccessToken(result.data.access_token);

    tempToken = "";
    localStorage.removeItem("tempToken");
    updateTokenBoxes();

    setStatus("2FA login successful. Access token saved.", "success");
  } else {
    setStatus("2FA login worked, but no access token was returned.", "warning");
  }

  show(result);
}

function stopBankIdPolling() {
  if (bankIdPollTimer) {
    clearInterval(bankIdPollTimer);
    bankIdPollTimer = null;
  }

  bankIdPollAttempts = 0;
}

function startBankIdPolling(orderRef) {
  if (!orderRef) {
    setStatus("No orderRef found. Cannot start BankID polling.", "warning");
    return;
  }

  stopBankIdPolling();

  bankIdPollAttempts = 0;

  setStatus("Waiting for BankID approval...", "loading");

  pollBankIdStatus(orderRef);

  bankIdPollTimer = setInterval(() => {
    pollBankIdStatus(orderRef);
  }, BANKID_POLL_INTERVAL_MS);
}

async function pollBankIdStatus(orderRef) {
  bankIdPollAttempts += 1;

  const result = await request(`/auth/bankid/status/${orderRef}`);

  show({
    message: "Automatic BankID status check",
    attempt: bankIdPollAttempts,
    result,
  });

  if (!result.ok) {
    stopBankIdPolling();
    setStatus(`BankID status failed: ${getErrorMessage(result)}`, "error");
    return;
  }

  const status = result.data.status;
  const hintCode = result.data.hintCode;

  if (status === "complete") {
    stopBankIdPolling();

    if (result.data.access_token) {
      saveAccessToken(result.data.access_token);
      setStatus("BankID login complete. Access token saved.", "success");
    } else {
      setStatus("BankID completed, but no access token was returned.", "warning");
    }

    show(result);
    return;
  }

  if (status === "failed") {
    stopBankIdPolling();
    setStatus(`BankID failed. Hint: ${hintCode || "No hint"}`, "error");
    show(result);
    return;
  }

  if (bankIdPollAttempts >= BANKID_MAX_POLL_ATTEMPTS) {
    stopBankIdPolling();
    setStatus("BankID check timed out. Try initiating BankID again.", "warning");
    show(result);
    return;
  }

  setStatus(
    `Waiting for BankID approval... Status: ${status || "unknown"}${
      hintCode ? `, hint: ${hintCode}` : ""
    }`,
    "loading"
  );
}

async function bankIdInitiate() {
  setStatus("Starting BankID authentication...", "loading");

  stopBankIdPolling();

  const result = await request("/auth/bankid/initiate", {
    method: "POST",
    body: JSON.stringify({}),
  });

  if (!result.ok) {
    setStatus(`BankID initiate failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  if (result.data.orderRef) {
    document.getElementById("bankIdOrderRef").value = result.data.orderRef;
  }

  if (result.data.autoStartToken) {
    document.getElementById("bankIdAutoStartToken").value =
      result.data.autoStartToken;
  }

  setStatus(
    "BankID initiated. Open the BankID app and approve. Status will update automatically.",
    "success"
  );

  show(result);

  if (result.data.orderRef) {
    startBankIdPolling(result.data.orderRef);
  }
}

function openBankIdApp() {
  const token = document.getElementById("bankIdAutoStartToken").value;
  const orderRef = document.getElementById("bankIdOrderRef").value;

  if (!token) {
    setStatus("No autoStartToken found. Click BankID initiate first.", "warning");
    show({
      error: "No autoStartToken found. Click BankID initiate first.",
    });
    return;
  }

  const url = `bankid:///?autostarttoken=${token}&redirect=null`;

  window.location.href = url;

  setStatus("BankID app opened. Waiting for approval...", "loading");

  show({
    message: "BankID app opened. Waiting for approval...",
    url,
    orderRef,
  });

  if (orderRef) {
    startBankIdPolling(orderRef);
  }
}

async function bankIdStatus() {
  setStatus("Checking BankID status manually...", "loading");

  const orderRef = document.getElementById("bankIdOrderRef").value;

  if (!orderRef) {
    setStatus("No orderRef found. Click BankID initiate first.", "warning");
    show({
      error: "No orderRef found. Click BankID initiate first.",
    });
    return;
  }

  const result = await request(`/auth/bankid/status/${orderRef}`);

  if (!result.ok) {
    setStatus(`BankID status failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  if (result.data.status === "complete") {
    stopBankIdPolling();

    if (result.data.access_token) {
      saveAccessToken(result.data.access_token);
      setStatus("BankID login complete. Access token saved.", "success");
    } else {
      setStatus("BankID completed, but no access token was returned.", "warning");
    }

    show(result);
    return;
  }

  setStatus(
    `BankID status: ${result.data.status || "unknown"}. Hint: ${
      result.data.hintCode || "No hint"
    }`,
    "warning"
  );

  show(result);
}