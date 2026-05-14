const API_BASE =
   window.location.origin && window.location.origin !== "null"
      ? window.location.origin
      : "http://localhost:8000";

const PAGE_LANG = document.documentElement.lang || "sv";

const DEFAULT_POSITION = { lat: 60.4858, lon: 15.4358 };
const SEARCH_RADIUS_KM = 150;

const visitorModal = document.getElementById("unescoModal");
const memberModal = document.getElementById("memberModal");
const openBtn = document.getElementById("openAdBtn");
const closeAdBtn = document.getElementById("closeAdBtn");
const closeMemberBtn = document.getElementById("closeMemberBtn");
const toMemberLink = document.getElementById("toMemberView");
const bankidBtn = document.getElementById("bankidBtn");
const subscribeForm = document.getElementById("subscribeForm");
const widgetStatus = document.getElementById("widgetStatus");
const loginForm = document.getElementById("loginForm");
const twoFactorForm = document.getElementById("twoFactorForm");
const loginStatus = document.getElementById("loginStatus");
const siteList = document.getElementById("siteList");
const siteSummary = document.getElementById("siteSummary");
const siteDetail = document.getElementById("siteDetail");
const detailTitle = document.getElementById("detailTitle");
const detailDescription = document.getElementById("detailDescription");
const languageSelect = document.getElementById("languageSelect");
const memberSiteText = document.getElementById("memberSiteText");
const visitedCheck = document.getElementById("visitedCheck");
const cancelSubscriptionBtn = document.getElementById("cancelSubscriptionBtn");

let lastFocusedElement;
let currentPosition = { ...DEFAULT_POSITION };
let sites = [];
let selectedSite = null;
let visitorMap = null;
let memberMap = null;
let tempToken = null;
let widgetLoaded = false;
let pendingEmail = null;

function openModal(modal) {
   lastFocusedElement = document.activeElement;
   modal.style.display = "flex";
   document.body.style.overflow = "hidden";
   modal.querySelector(".close-modal").focus();
}

function closeModal(modal) {
   modal.style.display = "none";
   document.body.style.overflow = "auto";
   if (lastFocusedElement) lastFocusedElement.focus();
}

function setStatus(element, message, isError = false) {
   element.textContent = message;
   element.classList.toggle("is-error", isError);
}

function escapeHtml(value) {
   return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
}

async function apiFetch(path, options = {}) {
   const token = sessionStorage.getItem("auth_token");
   const response = await fetch(`${API_BASE}${path}`, {
      headers: {
         "Content-Type": "application/json",
         ...(token ? { "Authorization": `Bearer ${token}` } : {}),
         ...(options.headers || {}),
      },
      ...restOptions,
   });

   let payload = null;
   try {
      payload = await response.json();
   } catch {
      payload = {};
   }

   if (!response.ok) {
      const detail = payload.detail || payload.error || "Anropet misslyckades.";
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
   }

   return payload;
}

function getSiteId(site) {
   return String(site.id_no || site.id || site.name_en || "site");
}

function getCoordinates(site) {
   const coords = site.coordinates || {};
   if (typeof coords.lat === "number" && typeof coords.lon === "number") {
      return { lat: coords.lat, lon: coords.lon };
   }
   return null;
}

function getPosition() {
   return new Promise((resolve) => {
      if (!navigator.geolocation) {
         resolve({ ...DEFAULT_POSITION });
         return;
      }

      navigator.geolocation.getCurrentPosition(
         (position) => {
            resolve({
               lat: position.coords.latitude,
               lon: position.coords.longitude,
            });
         },
         () => resolve({ ...DEFAULT_POSITION }),
         { enableHighAccuracy: true, timeout: 6000, maximumAge: 300000 }
      );
   });
}

function resetMap(containerId) {
   const container = document.getElementById(containerId);
   container.classList.add("map-loaded");
   container.innerHTML = "";
}

function renderMap(containerId, mapRefName) {
   if (!window.L) {
      document.getElementById(containerId).textContent = "Kartan kunde inte laddas.";
      return null;
   }

   resetMap(containerId);
   const existingMap = mapRefName === "visitor" ? visitorMap : memberMap;
   if (existingMap) {
      existingMap.remove();
   }

   const map = L.map(containerId).setView([currentPosition.lat, currentPosition.lon], 8);
   L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
   }).addTo(map);

   L.marker([currentPosition.lat, currentPosition.lon])
      .addTo(map)
      .bindPopup("Din position");

   sites.forEach((site) => {
      const coords = getCoordinates(site);
      if (!coords) return;
      L.marker([coords.lat, coords.lon])
         .addTo(map)
         .bindPopup(site.name_en || "UNESCO World Heritage Site")
         .on("click", () => selectSite(site));
   });

   setTimeout(() => map.invalidateSize(), 100);
   if (mapRefName === "visitor") visitorMap = map;
   if (mapRefName === "member") memberMap = map;
   return map;
}

function renderSiteSummary() {
   if (!sites.length) {
      siteSummary.innerHTML = `
         <h3>Upptäck platsen</h3>
         <p>Inga världsarv hittades inom ${SEARCH_RADIUS_KM} km. Testar du utan platsdelning används Borlänge som standard.</p>
      `;
      memberSiteText.textContent = "Inga världsarv hittades i närheten.";
      return;
   }

   const nearest = sites[0];
   const distance = nearest.distance_km ? `${nearest.distance_km} km bort` : "i närheten";
   siteSummary.innerHTML = `
      <h3>Upptäck platsen</h3>
      <p>Du är nära <strong>${escapeHtml(nearest.name_en || "ett världsarv")}</strong>, ${escapeHtml(distance)}.</p>
   `;
   memberSiteText.innerHTML = `Du befinner dig nära <strong>${escapeHtml(nearest.name_en || "ett världsarv")}</strong>.`;
}

function renderSites() {
   siteList.innerHTML = "";
   sites.slice(0, 5).forEach((site) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "site-card";
      button.dataset.siteId = getSiteId(site);

      const title = document.createElement("strong");
      title.textContent = site.name_en || "Okänt världsarv";
      const meta = document.createElement("span");
      meta.className = "site-meta";
      meta.textContent = [
         site.category,
         site.states_names,
         site.distance_km ? `${site.distance_km} km` : null,
      ].filter(Boolean).join(" · ");

      button.append(title, meta);
      button.addEventListener("click", () => selectSite(site));
      siteList.appendChild(button);
   });
}

function selectSite(site) {
   selectedSite = site;
   languageSelect.value = "sv";
   detailTitle.textContent = site.name_en || "UNESCO World Heritage Site";
   detailDescription.textContent =
      site.short_description_en || "Ingen beskrivning hittades i UNESCO-datat.";
   siteDetail.hidden = false;

   document.querySelectorAll(".site-card").forEach((card) => {
      card.classList.toggle("is-active", card.dataset.siteId === getSiteId(site));
   });

   translateSelectedSite();
}

async function loadWidgetData() {
   setStatus(widgetStatus, "Hämtar din position...");
   currentPosition = await getPosition();

   setStatus(widgetStatus, "Hämtar världsarv från backend...");
   sites = await apiFetch(
      `/unesco/sites?lat=${currentPosition.lat}&lon=${currentPosition.lon}&radius=${SEARCH_RADIUS_KM}`
   );

   renderSiteSummary();
   renderSites();
   renderMap("map-view", "visitor");
   if (sites.length) selectSite(sites[0]);
   setStatus(widgetStatus, "Redo.");
}

async function ensureWidgetLoaded() {
   if (widgetLoaded) {
      setTimeout(() => visitorMap?.invalidateSize(), 100);
      return;
   }

   try {
      await loadWidgetData();
      widgetLoaded = true;
   } catch (error) {
      setStatus(widgetStatus, error.message, true);
      siteSummary.innerHTML = "<h3>Upptäck platsen</h3><p>Kunde inte hämta världsarv just nu.</p>";
   }
}

async function translateSelectedSite() {
   if (!selectedSite || !languageSelect.value) {
      if (selectedSite) {
         detailDescription.textContent =
            selectedSite.short_description_en || "Ingen beskrivning hittades i UNESCO-datat.";
      }
      return;
   }

   detailDescription.textContent = "Översätter...";
   try {
      const result = await apiFetch("/translation/translate", {
         method: "POST",
         body: JSON.stringify({
            text: selectedSite.short_description_en || selectedSite.name_en || "",
            target_language: languageSelect.value,
         }),
      });
      detailDescription.textContent = result.translated_text;
   } catch (error) {
      detailDescription.textContent = error.message;
   }
}

async function sendChatMessage() {
   const input = document.getElementById("chatInput");
   const output = document.getElementById("chatOutput");
   const message = input.value.trim();
   if (!message) return;

   output.innerHTML += `<br><strong>Du:</strong> ${escapeHtml(message)}<br><strong>AI:</strong> Laddar...`;
   input.value = "";
   output.scrollTop = output.scrollHeight;

   const token = sessionStorage.getItem("auth_token");
   try {
      const result = await apiFetch("/unesco/chat", {
         method: "POST",
         headers: token ? { Authorization: `Bearer ${token}` } : {},
         body: JSON.stringify({
            message,
            lat: currentPosition.lat,
            lon: currentPosition.lon,
            radius: SEARCH_RADIUS_KM,
            page_lang: PAGE_LANG,
         }),
      });
      output.innerHTML = output.innerHTML.replace("Laddar...", escapeHtml(result.answer));
   } catch (error) {
      output.innerHTML = output.innerHTML.replace("Laddar...", escapeHtml(error.message));
   }
   output.scrollTop = output.scrollHeight;
}

let _isBankIdUser = false;
let _bankidInMemberModal = false;

async function showLoggedIn(isBankId = false) {
   _isBankIdUser = isBankId;
   loginForm.hidden = true;
   twoFactorForm.hidden = true;
   setStatus(loginStatus, "");
   document.getElementById("memberBankidSection").hidden = true;
   document.getElementById("memberSiteCard").hidden = false;
   document.getElementById("memberMapHeader").textContent = "Din Premium-karta";
   document.getElementById("userInfoPanel").hidden = false;
   document.getElementById("chatbotContainer").hidden = false;

   try {
      const user = await apiFetch("/auth/me");
      document.getElementById("userNameDisplay").textContent = user.full_name || user.email;
      document.getElementById("userEmailDisplay").textContent = user.full_name ? user.email : "";
   } catch { /* token may not be set yet, ignore */ }

   if (!isBankId) {
      document.getElementById("twoFaPanel").hidden = false;
      load2faStatus();
   }
}

function logout() {
   sessionStorage.removeItem("auth_token");
   _isBankIdUser = false;
   _bankidInMemberModal = false;
   document.getElementById("userInfoPanel").hidden = true;
   document.getElementById("userNameDisplay").textContent = "";
   document.getElementById("userEmailDisplay").textContent = "";
   document.getElementById("chatbotContainer").hidden = true;
   document.getElementById("twoFaPanel").hidden = true;
   document.getElementById("twoFaSetupBox").hidden = true;
   document.getElementById("twoFaDisableBox").hidden = true;
   document.getElementById("twoFaQrCode").innerHTML = "";
   document.getElementById("memberBankidSection").hidden = false;
   document.getElementById("memberSiteCard").hidden = true;
   document.getElementById("memberBankidChoicePanel").style.display = "none";
   document.getElementById("memberBankidQrPanel").hidden = true;
   document.getElementById("memberBankidQrCode").innerHTML = "";
   document.getElementById("memberMapHeader").textContent = "Interaktiv karta";
   loginForm.hidden = false;
   loginForm.reset();
   twoFactorForm.hidden = true;
   setStatus(loginStatus, "Du är utloggad.");
}

async function load2faStatus() {
   const twoFaStatus = document.getElementById("twoFaStatus");
   try {
      const result = await apiFetch("/auth/2fa/status");
      const enabled = result.two_factor_enabled;
      document.getElementById("twoFaStatusText").textContent = `Status: ${enabled ? "Aktiv" : "Inaktiv"}`;
      const btn = document.getElementById("twoFaActionBtn");
      btn.textContent = enabled ? "Inaktivera 2FA" : "Aktivera 2FA";
      btn.dataset.enabled = String(enabled);
      document.getElementById("twoFaSetupBox").hidden = true;
      document.getElementById("twoFaDisableBox").hidden = true;
      setStatus(twoFaStatus, "");
   } catch (error) {
      setStatus(twoFaStatus, error.message, true);
   }
}

async function handle2faAction() {
   const btn = document.getElementById("twoFaActionBtn");
   const twoFaStatus = document.getElementById("twoFaStatus");

   if (btn.dataset.enabled === "true") {
      document.getElementById("twoFaDisableBox").hidden = false;
      document.getElementById("twoFaSetupBox").hidden = true;
      return;
   }

   try {
      const result = await apiFetch("/auth/2fa/setup", { method: "POST" });
      const qrEl = document.getElementById("twoFaQrCode");
      qrEl.innerHTML = "";
      new QRCode(qrEl, { text: result.provisioning_uri, width: 180, height: 180 });
      document.getElementById("twoFaSetupBox").hidden = false;
      document.getElementById("twoFaDisableBox").hidden = true;
      setStatus(twoFaStatus, "Skanna QR-koden och ange koden nedan.");
   } catch (error) {
      setStatus(twoFaStatus, error.message, true);
   }
}

async function verify2faEnable() {
   const code = document.getElementById("twoFaCodeInput").value.trim();
   const twoFaStatus = document.getElementById("twoFaStatus");
   if (!code) return;
   try {
      await apiFetch("/auth/2fa/enable", { method: "POST", body: JSON.stringify({ code }) });
      document.getElementById("twoFaCodeInput").value = "";
      setStatus(twoFaStatus, "2FA aktiverat!");
      load2faStatus();
   } catch (error) {
      setStatus(twoFaStatus, error.message, true);
   }
}

async function verify2faDisable() {
   const code = document.getElementById("twoFaDisableCodeInput").value.trim();
   const twoFaStatus = document.getElementById("twoFaStatus");
   if (!code) return;
   try {
      await apiFetch("/auth/2fa/disable", { method: "POST", body: JSON.stringify({ code }) });
      document.getElementById("twoFaDisableCodeInput").value = "";
      setStatus(twoFaStatus, "2FA inaktiverat.");
      load2faStatus();
   } catch (error) {
      setStatus(twoFaStatus, error.message, true);
   }
}

async function generateBankIdQrData(qrStartToken, qrStartSecret, seconds) {
   const keyBytes = new Uint8Array(qrStartSecret.replace(/-/g, "").match(/.{2}/g).map(b => parseInt(b, 16)));
   const key = await crypto.subtle.importKey(
      "raw", keyBytes,
      { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
   );
   const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(String(seconds)));
   const hex = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 8);
   return `bankid.${qrStartToken}.${seconds}.${hex}`;
}

let _bankidPollTimer = null;
let _bankidQrInterval = null;

function _stopBankId() {
   if (_bankidPollTimer) { clearTimeout(_bankidPollTimer); _bankidPollTimer = null; }
   if (_bankidQrInterval) { clearInterval(_bankidQrInterval); _bankidQrInterval = null; }
}

function _hideBankIdChoice() {
   document.getElementById("bankidChoicePanel").style.display = "none";
}

function _hideBankIdQr() {
   if (_bankidInMemberModal) {
      const panel = document.getElementById("memberBankidQrPanel");
      panel.hidden = true;
      document.getElementById("memberBankidQrCode").innerHTML = "";
   } else {
      const panel = document.getElementById("bankidQrPanel");
      panel.hidden = true;
      document.getElementById("bankidQrCode").innerHTML = "";
   }
   _stopBankId();
}

function _onBankIdComplete(accessToken) {
   _stopBankId();
   _hideBankIdQr();
   if (accessToken) sessionStorage.setItem("auth_token", accessToken);
   if (_bankidInMemberModal) {
      setStatus(document.getElementById("memberBankidStatus"), "");
      document.getElementById("memberBankidBtn").disabled = false;
      showLoggedIn(true);
      if (sites.length) renderMap("member-map-view", "member");
   } else {
      setStatus(widgetStatus, "Inloggad med BankID.");
      bankidBtn.disabled = false;
      closeModal(visitorModal);
      openModal(memberModal);
      showLoggedIn(true);
      if (sites.length) renderMap("member-map-view", "member");
   }
}

function _pollBankIdStatus(orderRef) {
   const maxAttempts = 45;
   let attempts = 0;

   const poll = async () => {
      const statusEl = _bankidInMemberModal ? document.getElementById("memberBankidStatus") : widgetStatus;
      const activeBtn = _bankidInMemberModal ? document.getElementById("memberBankidBtn") : bankidBtn;

      if (attempts >= maxAttempts) {
         _stopBankId();
         _hideBankIdQr();
         setStatus(statusEl, "BankID tog för lång tid. Försök igen.", true);
         activeBtn.disabled = false;
         return;
      }
      attempts++;

      try {
         const status = await apiFetch(`/auth/bankid/status/${orderRef}`);

         if (status.status === "complete") {
            _onBankIdComplete(status.access_token);
         } else if (status.status === "failed") {
            _stopBankId();
            _hideBankIdQr();
            const reason = status.hintCode || status.errorCode || "okänt fel";
            setStatus(statusEl, `BankID misslyckades: ${reason}`, true);
            activeBtn.disabled = false;
         } else {
            const hint = status.hintCode ? ` (${status.hintCode})` : "";
            setStatus(statusEl, `Väntar på BankID${hint}...`);
            _bankidPollTimer = setTimeout(poll, 2000);
         }
      } catch (error) {
         _stopBankId();
         _hideBankIdQr();
         setStatus(statusEl, error.message, true);
         activeBtn.disabled = false;
      }
   };

   _bankidPollTimer = setTimeout(poll, 2000);
}

function initiateBankId() {
   document.getElementById("bankidChoicePanel").style.display = "flex";
}

async function startBankIdDevice() {
   _bankidInMemberModal = false;
   _hideBankIdChoice();
   setStatus(widgetStatus, "Öppnar BankID...");
   bankidBtn.disabled = true;

   try {
      const initiated = await apiFetch("/auth/bankid/initiate", { method: "POST" });
      const link = document.createElement("a");
      link.href = `bankid:///autostarttoken=${initiated.autoStartToken}&redirect=null`;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      _pollBankIdStatus(initiated.orderRef);
   } catch (error) {
      setStatus(widgetStatus, error.message, true);
      bankidBtn.disabled = false;
   }
}

async function startBankIdMobile() {
   _bankidInMemberModal = false;
   _hideBankIdChoice();
   setStatus(widgetStatus, "Förbereder QR-kod...");
   bankidBtn.disabled = true;

   try {
      const initiated = await apiFetch("/auth/bankid/initiate", { method: "POST" });
      const { orderRef } = initiated;

      const qrPanel = document.getElementById("bankidQrPanel");
      const qrEl = document.getElementById("bankidQrCode");
      qrEl.innerHTML = "";
      qrPanel.hidden = false;

      let qrInstance = null;

      const updateQr = async () => {
         try {
            const result = await apiFetch(`/auth/bankid/qr/${orderRef}`);
            const qrData = result.qr_data;
            if (qrInstance) {
               qrInstance.clear();
               qrInstance.makeCode(qrData);
            } else {
               qrInstance = new QRCode(qrEl, { text: qrData, width: 250, height: 250, correctLevel: QRCode.CorrectLevel.L });
            }
         } catch { /* ignore transient errors during QR refresh */ }
      };

      await updateQr();
      _bankidQrInterval = setInterval(updateQr, 1000);
      _pollBankIdStatus(orderRef);
   } catch (error) {
      setStatus(widgetStatus, error.message, true);
      bankidBtn.disabled = false;
   }
}

function initiateMemberBankId() {
   document.getElementById("memberBankidChoicePanel").style.display = "flex";
}

function _hideMemberBankidChoice() {
   document.getElementById("memberBankidChoicePanel").style.display = "none";
}

async function startMemberBankIdDevice() {
   _bankidInMemberModal = true;
   _hideMemberBankidChoice();
   const statusEl = document.getElementById("memberBankidStatus");
   const btn = document.getElementById("memberBankidBtn");
   setStatus(statusEl, "Öppnar BankID...");
   btn.disabled = true;

   try {
      const initiated = await apiFetch("/auth/bankid/initiate", { method: "POST" });
      const link = document.createElement("a");
      link.href = `bankid:///autostarttoken=${initiated.autoStartToken}&redirect=null`;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      _pollBankIdStatus(initiated.orderRef);
   } catch (error) {
      setStatus(statusEl, error.message, true);
      btn.disabled = false;
   }
}

async function startMemberBankIdMobile() {
   _bankidInMemberModal = true;
   _hideMemberBankidChoice();
   const statusEl = document.getElementById("memberBankidStatus");
   const btn = document.getElementById("memberBankidBtn");
   setStatus(statusEl, "Förbereder QR-kod...");
   btn.disabled = true;

   try {
      const initiated = await apiFetch("/auth/bankid/initiate", { method: "POST" });
      const { orderRef } = initiated;

      const qrPanel = document.getElementById("memberBankidQrPanel");
      const qrEl = document.getElementById("memberBankidQrCode");
      qrEl.innerHTML = "";
      qrPanel.hidden = false;

      let qrInstance = null;

      const updateQr = async () => {
         try {
            const result = await apiFetch(`/auth/bankid/qr/${orderRef}`);
            const qrData = result.qr_data;
            if (qrInstance) {
               qrInstance.clear();
               qrInstance.makeCode(qrData);
            } else {
               qrInstance = new QRCode(qrEl, { text: qrData, width: 250, height: 250, correctLevel: QRCode.CorrectLevel.L });
            }
         } catch { /* ignore transient errors during QR refresh */ }
      };

      await updateQr();
      _bankidQrInterval = setInterval(updateQr, 1000);
      _pollBankIdStatus(orderRef);
   } catch (error) {
      setStatus(statusEl, error.message, true);
      btn.disabled = false;
   }
}

async function subscribe(event) {
   event.preventDefault();
   const phone = document.getElementById("phoneInput").value.trim();
   const name = document.getElementById("nameInput").value.trim();
   const email = document.getElementById("emailInput").value.trim();
   const password = document.getElementById("passwordInput").value;
   const method = document.getElementById("paymentMethod").value;
   const siteId = selectedSite ? getSiteId(selectedSite) : "unknown_site";

   let userId = sessionStorage.getItem("auth_token");

   if (!userId) {
      if (!email) {
         setStatus(widgetStatus, "Ange e-post för att skapa konto.", true);
         return;
      }
      if (!password || password.length < 8) {
         setStatus(widgetStatus, "Lösenordet måste vara minst 8 tecken.", true);
         return;
      }

      setStatus(widgetStatus, "Skapar konto...");
      try {
         await apiFetch("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, full_name: name || null }),
         });
      } catch (error) {
         setStatus(widgetStatus, error.message, true);
         return;
      }

      setStatus(widgetStatus, "Loggar in...");
      try {
         const loginResult = await apiFetch("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
         });
         sessionStorage.setItem("auth_token", loginResult.access_token);
         userId = loginResult.access_token;
      } catch (error) {
         setStatus(widgetStatus, error.message, true);
         return;
      }
   }

   setStatus(widgetStatus, "Aktiverar prenumeration...");
   try {
      await apiFetch("/api/notification/subscribe", {
         method: "POST",
         body: JSON.stringify({
            user_id: userId,
            phone: phone || null,
            email: email || null,
            sites: [siteId],
         }),
      });

      const payment = await apiFetch("/payment/create", {
         method: "POST",
         body: JSON.stringify({ user_id: userId, plan_id: "plan_basic", method }),
      });

      if (method === "card" && payment.url) {
         window.location.href = payment.url;
         return;
      }

      setStatus(widgetStatus, "Konto skapat och prenumeration aktiverad!");
      setTimeout(() => {
         closeModal(visitorModal);
         openModal(memberModal);
         showLoggedIn(false);
         if (sites.length) renderMap("member-map-view", "member");
      }, 1500);
   } catch (error) {
      setStatus(widgetStatus, error.message, true);
   }
}

async function login(event) {
   event.preventDefault();
   setStatus(loginStatus, "Loggar in...");

   try {
      const result = await apiFetch("/auth/login", {
         method: "POST",
         body: JSON.stringify({
            email: document.getElementById("loginEmail").value.trim(),
            password: document.getElementById("loginPassword").value,
         }),
      });

      if (result.requires_2fa) {
         tempToken = result.temp_token;
         twoFactorForm.hidden = false;
         setStatus(loginStatus, "Ange din tvåfaktorskod.");
         return;
      }

      sessionStorage.setItem("auth_token", result.access_token);
      sessionStorage.setItem("user_email", document.getElementById("loginEmail").value.trim());
      setStatus(loginStatus, "Inloggad.");
      showLoggedIn();
   } catch (error) {
      setStatus(loginStatus, error.message, true);
   }
}

async function completeTwoFactor(event) {
   event.preventDefault();
   setStatus(loginStatus, "Verifierar kod...");

   try {
      const result = await apiFetch("/auth/login/2fa", {
         method: "POST",
         body: JSON.stringify({
            temp_token: tempToken,
            code: document.getElementById("twoFactorCode").value.trim(),
         }),
      });
      sessionStorage.setItem("auth_token", result.access_token);
      setStatus(loginStatus, "Inloggad.");
      showLoggedIn();
   } catch (error) {
      setStatus(loginStatus, error.message, true);
   }
}

async function markVisited() {
   if (!selectedSite || !visitedCheck.checked) return;

   try {
      await apiFetch("/api/notification/mark-visited", {
         method: "POST",
         body: JSON.stringify({
            user_id: sessionStorage.getItem("auth_token") || "guest",
            site_id: getSiteId(selectedSite),
         }),
      });
      setStatus(loginStatus, "Platsen markerades som besökt.");
   } catch (error) {
      setStatus(loginStatus, error.message, true);
   }
}

async function saveCredentials(event) {
   event.preventDefault();
   const statusEl = document.getElementById("setPasswordStatus");
   const email = pendingEmail || document.getElementById("setupEmail").value.trim();
   const password = document.getElementById("newPassword").value;
   const confirm = document.getElementById("confirmPassword").value;

   if (!email) {
      setStatus(statusEl, "Ange en e-postadress.", true);
      return;
   }
   if (password.length < 8) {
      setStatus(statusEl, "Lösenordet måste vara minst 8 tecken.", true);
      return;
   }
   if (password !== confirm) {
      setStatus(statusEl, "Lösenorden matchar inte.", true);
      return;
   }

   setStatus(statusEl, "Sparar...");
   try {
      await apiFetch("/auth/register", {
         method: "POST",
         body: JSON.stringify({ email, password }),
      });
      setStatus(statusEl, "Konto klart! Du kan nu logga in på Mina Sidor.");
      setTimeout(() => {
         visitorModal.style.display = "none";
         openModal(memberModal);
      }, 2000);
   } catch (error) {
      setStatus(statusEl, error.message, true);
   }
}

openBtn.addEventListener("click", () => {
   openModal(visitorModal);
   ensureWidgetLoaded();
});

closeAdBtn.addEventListener("click", () => closeModal(visitorModal));
closeMemberBtn.addEventListener("click", () => closeModal(memberModal));

toMemberLink.addEventListener("click", (event) => {
   event.preventDefault();
   visitorModal.style.display = "none";
   openModal(memberModal);
   showChatIfLoggedIn();
   if (sites.length) {
      renderMap("member-map-view", "member");
   }
});

document.getElementById("backToVisitorBtn").addEventListener("click", () => {
   closeModal(memberModal);
   openModal(visitorModal);
   setTimeout(() => visitorMap?.invalidateSize(), 100);
});

bankidBtn.addEventListener("click", initiateBankId);
document.getElementById("bankidDeviceBtn").addEventListener("click", startBankIdDevice);
document.getElementById("bankidMobileBtn").addEventListener("click", startBankIdMobile);
document.getElementById("bankidQrCancelBtn").addEventListener("click", () => {
   _hideBankIdQr();
   bankidBtn.disabled = false;
   setStatus(widgetStatus, "");
   document.getElementById("bankidChoicePanel").style.display = "flex";
});
subscribeForm.addEventListener("submit", subscribe);
loginForm.addEventListener("submit", login);
twoFactorForm.addEventListener("submit", completeTwoFactor);
languageSelect.addEventListener("change", translateSelectedSite);
visitedCheck.addEventListener("change", markVisited);
document.getElementById("sendChat").addEventListener("click", sendChatMessage);
document.getElementById("chatInput").addEventListener("keydown", (event) => {
   if (event.key === "Enter") sendChatMessage();
});
cancelSubscriptionBtn.addEventListener("click", () => {
   document.getElementById("cancelConfirm").hidden = false;
});

document.getElementById("confirmCancelNo").addEventListener("click", () => {
   document.getElementById("cancelConfirm").hidden = true;
});

document.getElementById("confirmCancelYes").addEventListener("click", async () => {
   const token = sessionStorage.getItem("auth_token");
   if (!token) {
      setStatus(loginStatus, "Du är inte inloggad.", true);
      return;
   }
   const userEmail = sessionStorage.getItem("user_email");
   try {
      setStatus(loginStatus, "Avslutar prenumeration...");
      document.getElementById("cancelConfirm").hidden = true;
      if (userEmail) {
         await apiFetch("/api/notification/unsubscribe", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: JSON.stringify({ user_id: userEmail }),
         });
      }
      await apiFetch("/auth/account", {
         method: "DELETE",
         headers: { Authorization: `Bearer ${token}` },
      });
      sessionStorage.removeItem("auth_token");
      sessionStorage.removeItem("user_email");
      document.getElementById("setPasswordSection").hidden = true;
      document.getElementById("subscribeForm").hidden = false;
      document.getElementById("widgetStatus").textContent = "";
      closeModal(memberModal);
      openModal(visitorModal);
   } catch (error) {
      setStatus(loginStatus, error.message, true);
   }
});
document.getElementById("backToVisitorBtn").addEventListener("click", () => {
   closeModal(memberModal);
   openModal(visitorModal);
});
document.getElementById("logoutBtn").addEventListener("click", logout);
document.getElementById("twoFaActionBtn").addEventListener("click", handle2faAction);
document.getElementById("twoFaVerifyBtn").addEventListener("click", verify2faEnable);
document.getElementById("twoFaDisableVerifyBtn").addEventListener("click", verify2faDisable);
document.getElementById("memberBankidBtn").addEventListener("click", initiateMemberBankId);
document.getElementById("memberBankidDeviceBtn").addEventListener("click", startMemberBankIdDevice);
document.getElementById("memberBankidMobileBtn").addEventListener("click", startMemberBankIdMobile);
document.getElementById("memberBankidQrCancelBtn").addEventListener("click", () => {
   _hideBankIdQr();
   document.getElementById("memberBankidBtn").disabled = false;
   setStatus(document.getElementById("memberBankidStatus"), "");
   document.getElementById("memberBankidChoicePanel").style.display = "flex";
});

window.addEventListener("click", (event) => {
   if (event.target.classList.contains("modal-overlay")) {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
});

document.addEventListener("keydown", (event) => {
   if (event.key === "Escape") {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
});
