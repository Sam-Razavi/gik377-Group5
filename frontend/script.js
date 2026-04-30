let accessToken = localStorage.getItem("accessToken") || "";
let tempToken = localStorage.getItem("tempToken") || "";

let bankIdPollTimer = null;
let bankIdPollAttempts = 0;

let mobileBankIdQrTimer = null;
let mobileBankIdQrStartTime = null;
let mobileBankIdQrStartToken = "";
let mobileBankIdQrStartSecret = "";

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

/* -----------------------------
   Location and profile helpers
----------------------------- */

function getBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported by this browser."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
      },
      (error) => {
        let message = "Could not get current location.";

        if (error.code === error.PERMISSION_DENIED) {
          message = "Location permission was denied.";
        }

        if (error.code === error.POSITION_UNAVAILABLE) {
          message = "Location information is unavailable.";
        }

        if (error.code === error.TIMEOUT) {
          message = "Location request timed out.";
        }

        reject(new Error(message));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

async function useCurrentLocationForRegister() {
  setStatus("Asking browser for your current location...", "loading");

  try {
    const location = await getBrowserLocation();

    document.getElementById("homeLat").value = location.latitude.toFixed(6);
    document.getElementById("homeLon").value = location.longitude.toFixed(6);

    if (!document.getElementById("homeAddress").value.trim()) {
      document.getElementById("homeAddress").value = "Current location";
    }

    setStatus(
      `Location added to register form. Accuracy: about ${Math.round(
        location.accuracy
      )} meters.`,
      "success"
    );

    show({
      message: "Current location added to register form",
      latitude: location.latitude,
      longitude: location.longitude,
      accuracy_meters: location.accuracy,
    });
  } catch (error) {
    setStatus(error.message, "error");
    show({
      error: error.message,
    });
  }
}

async function useCurrentLocationForProfile() {
  setStatus("Asking browser for your current location...", "loading");

  try {
    const location = await getBrowserLocation();

    document.getElementById("profileHomeLat").value =
      location.latitude.toFixed(6);
    document.getElementById("profileHomeLon").value =
      location.longitude.toFixed(6);

    if (!document.getElementById("profileHomeAddress").value.trim()) {
      document.getElementById("profileHomeAddress").value = "Current location";
    }

    setStatus(
      `Location added to profile form. Accuracy: about ${Math.round(
        location.accuracy
      )} meters. Click Update profile to save it.`,
      "success"
    );

    show({
      message: "Current location added to profile form",
      latitude: location.latitude,
      longitude: location.longitude,
      accuracy_meters: location.accuracy,
    });
  } catch (error) {
    setStatus(error.message, "error");
    show({
      error: error.message,
    });
  }
}

function fillProfileFormFromUser(user) {
  if (!user) return;

  document.getElementById("profileFullName").value = user.full_name || "";
  document.getElementById("profileHomeAddress").value =
    user.home_address || "";
  document.getElementById("profileHomeLat").value =
    user.home_lat !== null && user.home_lat !== undefined ? user.home_lat : "";
  document.getElementById("profileHomeLon").value =
    user.home_lon !== null && user.home_lon !== undefined ? user.home_lon : "";
}

function isProfileLocationIncomplete(user) {
  if (!user) return false;

  return (
    !user.home_address ||
    user.home_lat === null ||
    user.home_lat === undefined ||
    user.home_lon === null ||
    user.home_lon === undefined
  );
}

function checkProfileCompletion(user, source = "login") {
  if (!user) return;

  fillProfileFormFromUser(user);

  if (isProfileLocationIncomplete(user)) {
    setStatus(
      `${source} successful. Profile location is missing. Use the Profile / Location section to add it.`,
      "warning"
    );
  }
}

async function updateProfile() {
  setStatus("Updating profile...", "loading");

  if (!accessToken) {
    setStatus("You must login before updating your profile.", "warning");
    return;
  }

  const fullName = document.getElementById("profileFullName").value.trim();
  const homeAddress = document
    .getElementById("profileHomeAddress")
    .value.trim();
  const homeLat = document.getElementById("profileHomeLat").value.trim();
  const homeLon = document.getElementById("profileHomeLon").value.trim();

  const body = {};

  if (fullName) {
    body.full_name = fullName;
  }

  if (homeAddress) {
    body.home_address = homeAddress;
  }

  if (homeLat) {
    body.home_lat = parseFloat(homeLat);
  }

  if (homeLon) {
    body.home_lon = parseFloat(homeLon);
  }

  if (Object.keys(body).length === 0) {
    setStatus("No profile fields to update.", "warning");
    return;
  }

  const result = await request("/auth/me/profile", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!result.ok) {
    setStatus(`Profile update failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return;
  }

  fillProfileFormFromUser(result.data);

  setStatus("Profile updated successfully.", "success");
  show(result);
}

/* -----------------------------
   General auth
----------------------------- */

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
  const homeLat = document.getElementById("homeLat").value.trim();
  const homeLon = document.getElementById("homeLon").value.trim();

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

  fillProfileFormFromUser(result.data);

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

    const meResult = await request("/auth/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (meResult.ok) {
      fillProfileFormFromUser(meResult.data);
      checkProfileCompletion(meResult.data, "Login");
    }

    show(result);
  } else {
    setStatus("Login worked, but no access token was returned.", "warning");
    show(result);
  }
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

  fillProfileFormFromUser(result.data);

  if (isProfileLocationIncomplete(result.data)) {
    setStatus("Current user loaded. Profile location is missing.", "warning");
  } else {
    setStatus("Current user loaded successfully.", "success");
  }

  show(result);
}

/* -----------------------------
   2FA
----------------------------- */

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

    const meResult = await request("/auth/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (meResult.ok) {
      fillProfileFormFromUser(meResult.data);
      checkProfileCompletion(meResult.data, "2FA login");
    }
  } else {
    setStatus("2FA login worked, but no access token was returned.", "warning");
  }

  show(result);
}

/* -----------------------------
   BankID QR helpers
----------------------------- */

function stopMobileBankIdQr() {
  if (mobileBankIdQrTimer) {
    clearInterval(mobileBankIdQrTimer);
    mobileBankIdQrTimer = null;
  }

  mobileBankIdQrStartTime = null;
  mobileBankIdQrStartToken = "";
  mobileBankIdQrStartSecret = "";

  const qrWrapper = document.getElementById("mobileBankIdQrWrapper");
  const qrImage = document.getElementById("mobileBankIdQrImage");
  const qrDataBox = document.getElementById("mobileBankIdQrData");

  if (qrWrapper) {
    qrWrapper.classList.add("hidden");
  }

  if (qrImage) {
    qrImage.removeAttribute("src");
  }

  if (qrDataBox) {
    qrDataBox.textContent = "No QR data yet";
  }
}

async function hmacSha256Hex(secret, message) {
  const encoder = new TextEncoder();

  const keyData = encoder.encode(secret);
  const messageData = encoder.encode(message);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyData,
    {
      name: "HMAC",
      hash: "SHA-256",
    },
    false,
    ["sign"]
  );

  const signature = await crypto.subtle.sign("HMAC", cryptoKey, messageData);

  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function updateMobileBankIdQr() {
  if (
    !mobileBankIdQrStartTime ||
    !mobileBankIdQrStartToken ||
    !mobileBankIdQrStartSecret
  ) {
    return;
  }

  const elapsedSeconds = Math.floor(
    (Date.now() - mobileBankIdQrStartTime) / 1000
  ).toString();

  const qrAuthCode = await hmacSha256Hex(
    mobileBankIdQrStartSecret,
    elapsedSeconds
  );

  const qrData = `bankid.${mobileBankIdQrStartToken}.${elapsedSeconds}.${qrAuthCode}`;

  const qrImage = document.getElementById("mobileBankIdQrImage");
  const qrDataBox = document.getElementById("mobileBankIdQrData");

  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=190x190&data=${encodeURIComponent(
    qrData
  )}`;

  if (qrImage) {
    qrImage.src = qrUrl;
  }

  if (qrDataBox) {
    qrDataBox.textContent = qrData;
  }
}

function startMobileBankIdQr(qrStartToken, qrStartSecret) {
  const qrWrapper = document.getElementById("mobileBankIdQrWrapper");

  if (!qrStartToken || !qrStartSecret) {
    setStatus("Mobile BankID QR could not start because QR tokens are missing.", "error");
    return;
  }

  if (!qrWrapper) {
    setStatus("Mobile BankID QR HTML elements are missing.", "error");
    return;
  }

  stopMobileBankIdQr();

  mobileBankIdQrStartToken = qrStartToken;
  mobileBankIdQrStartSecret = qrStartSecret;
  mobileBankIdQrStartTime = Date.now();

  qrWrapper.classList.remove("hidden");

  updateMobileBankIdQr();

  mobileBankIdQrTimer = setInterval(() => {
    updateMobileBankIdQr();
  }, 1000);
}

/* -----------------------------
   BankID polling and flows
----------------------------- */

function stopBankIdPolling() {
  if (bankIdPollTimer) {
    clearInterval(bankIdPollTimer);
    bankIdPollTimer = null;
  }

  bankIdPollAttempts = 0;
  stopMobileBankIdQr();

  setStatus("BankID polling stopped.", "info");
}

function startBankIdPolling(orderRef) {
  if (!orderRef) {
    setStatus("No orderRef found. Cannot start BankID polling.", "warning");
    return;
  }

  if (bankIdPollTimer) {
    clearInterval(bankIdPollTimer);
    bankIdPollTimer = null;
  }

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
    if (bankIdPollTimer) {
      clearInterval(bankIdPollTimer);
      bankIdPollTimer = null;
    }

    bankIdPollAttempts = 0;
    stopMobileBankIdQr();

    if (result.data.access_token) {
      saveAccessToken(result.data.access_token);

      if (result.data.user) {
        fillProfileFormFromUser(result.data.user);

        if (isProfileLocationIncomplete(result.data.user)) {
          setStatus(
            "BankID login complete. Access token saved. Profile location is missing, please complete it.",
            "warning"
          );
        } else {
          setStatus("BankID login complete. Access token saved.", "success");
        }
      } else {
        setStatus("BankID login complete. Access token saved.", "success");
      }
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

async function initiateBankId() {
  const result = await request("/auth/bankid/initiate", {
    method: "POST",
    body: JSON.stringify({}),
  });

  if (!result.ok) {
    setStatus(`BankID initiate failed: ${getErrorMessage(result)}`, "error");
    show(result);
    return null;
  }

  if (result.data.orderRef) {
    document.getElementById("bankIdOrderRef").value = result.data.orderRef;
  }

  if (result.data.autoStartToken) {
    document.getElementById("bankIdAutoStartToken").value =
      result.data.autoStartToken;
  }

  show(result);
  return result;
}

async function bankIdSameDeviceStart() {
  setStatus("Starting BankID on this device...", "loading");

  stopBankIdPolling();

  const result = await initiateBankId();

  if (!result) return;

  if (result.data.orderRef) {
    startBankIdPolling(result.data.orderRef);
  }

  if (result.data.autoStartToken) {
    openBankIdApp();
  } else {
    setStatus("BankID started, but no autoStartToken was returned.", "warning");
  }
}

async function bankIdMobileQrStart() {
  setStatus("Starting Mobile BankID QR...", "loading");

  stopBankIdPolling();

  const result = await initiateBankId();

  if (!result) return;

  if (!result.data.qrStartToken || !result.data.qrStartSecret) {
    setStatus("Backend did not return qrStartToken or qrStartSecret.", "error");
    show(result);
    return;
  }

  startMobileBankIdQr(result.data.qrStartToken, result.data.qrStartSecret);

  setStatus(
    "Mobile BankID QR started. Scan the QR code with the BankID app on your phone.",
    "success"
  );

  if (result.data.orderRef) {
    startBankIdPolling(result.data.orderRef);
  }
}

async function bankIdInitiate() {
  setStatus("Starting BankID authentication...", "loading");

  stopBankIdPolling();

  const result = await initiateBankId();

  if (!result) return;

  setStatus(
    "BankID initiated. Choose Open BankID app for same-device login, or use Mobile BankID QR if visible.",
    "success"
  );

  if (result.data.orderRef) {
    startBankIdPolling(result.data.orderRef);
  }
}

function openBankIdApp() {
  const token = document.getElementById("bankIdAutoStartToken").value;
  const orderRef = document.getElementById("bankIdOrderRef").value;

  if (!token) {
    setStatus("No autoStartToken found. Start BankID on this device first.", "warning");
    show({
      error: "No autoStartToken found. Start BankID on this device first.",
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
    setStatus("No orderRef found. Start BankID first.", "warning");
    show({
      error: "No orderRef found. Start BankID first.",
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
    if (bankIdPollTimer) {
      clearInterval(bankIdPollTimer);
      bankIdPollTimer = null;
    }

    bankIdPollAttempts = 0;
    stopMobileBankIdQr();

    if (result.data.access_token) {
      saveAccessToken(result.data.access_token);

      if (result.data.user) {
        fillProfileFormFromUser(result.data.user);

        if (isProfileLocationIncomplete(result.data.user)) {
          setStatus(
            "BankID login complete. Access token saved. Profile location is missing, please complete it.",
            "warning"
          );
        } else {
          setStatus("BankID login complete. Access token saved.", "success");
        }
      } else {
        setStatus("BankID login complete. Access token saved.", "success");
      }
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