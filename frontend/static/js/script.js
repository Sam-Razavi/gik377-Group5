const API_BASE =
   window.location.origin && window.location.origin !== "null"
      ? window.location.origin
      : "http://localhost:8000";

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
   const response = await fetch(`${API_BASE}${path}`, {
      headers: {
         "Content-Type": "application/json",
         ...(options.headers || {}),
      },
      ...options,
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
   languageSelect.value = "";
   detailTitle.textContent = site.name_en || "UNESCO World Heritage Site";
   detailDescription.textContent =
      site.short_description_en || "Ingen beskrivning hittades i UNESCO-datat.";
   siteDetail.hidden = false;

   document.querySelectorAll(".site-card").forEach((card) => {
      card.classList.toggle("is-active", card.dataset.siteId === getSiteId(site));
   });
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

   try {
      const result = await apiFetch("/unesco/chat", {
         method: "POST",
         body: JSON.stringify({
            message,
            lat: currentPosition.lat,
            lon: currentPosition.lon,
            radius: SEARCH_RADIUS_KM,
         }),
      });
      output.innerHTML = output.innerHTML.replace("Laddar...", escapeHtml(result.answer));
   } catch (error) {
      output.innerHTML = output.innerHTML.replace("Laddar...", escapeHtml(error.message));
   }
   output.scrollTop = output.scrollHeight;
}

async function initiateBankId() {
   setStatus(widgetStatus, "Öppnar BankID...");
   bankidBtn.disabled = true;

   try {
      const initiated = await apiFetch("/auth/bankid/initiate", { method: "POST" });
      setTimeout(async () => {
         try {
            const status = await apiFetch(`/auth/bankid/status/${initiated.orderRef}`);
            if (status.status === "complete") {
               if (status.access_token) {
                  sessionStorage.setItem("auth_token", status.access_token);
               }
               setStatus(widgetStatus, "Inloggad med BankID.");
            } else {
               setStatus(widgetStatus, `BankID status: ${status.status}`);
            }
         } catch (error) {
            setStatus(widgetStatus, error.message, true);
         } finally {
            bankidBtn.disabled = false;
         }
      }, 2000);
   } catch (error) {
      setStatus(widgetStatus, error.message, true);
      bankidBtn.disabled = false;
   }
}

async function subscribe(event) {
   event.preventDefault();
   const phone = document.getElementById("phoneInput").value.trim();
   const email = document.getElementById("emailInput").value.trim();
   const method = document.getElementById("paymentMethod").value;
   const userId = sessionStorage.getItem("auth_token") || `guest_${Date.now()}`;
   const siteId = selectedSite ? getSiteId(selectedSite) : "unknown_site";

   if (!phone && !email) {
      setStatus(widgetStatus, "Ange mobilnummer eller e-post.", true);
      return;
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
         body: JSON.stringify({
            user_id: userId,
            plan_id: "plan_basic",
            method,
         }),
      });

      if (method === "card" && payment.url) {
         window.location.href = payment.url;
         return;
      }

      setStatus(widgetStatus, "Prenumeration aktiverad!");
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
      setStatus(loginStatus, "Inloggad.");
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
      twoFactorForm.hidden = true;
      setStatus(loginStatus, "Inloggad.");
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
   if (sites.length) {
      renderMap("member-map-view", "member");
   }
});

bankidBtn.addEventListener("click", initiateBankId);
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
   setStatus(loginStatus, "Prenumerationen kan avslutas via betalningsmodulen.");
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
