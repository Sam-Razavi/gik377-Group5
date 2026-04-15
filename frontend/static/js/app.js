// Amanda: Denna funktion renderar gränssnittet
function renderSites(sites) {
   const container = document.getElementById("sites-display");
   container.innerHTML = sites
      .map(
         (site) => `
         <div class="site-card">
             <h3>${site.name}</h3>
             <p>${site.description}</p>
         </div>
     `
      )
      .join("");
}

// Riyaaq: Lyssnare för SMS-tjänsten
document.getElementById("sms-form").addEventListener("submit", (e) => {
   e.preventDefault();
   const phone = document.getElementById("phone").value;
   console.log("Anropar Riyaaqs API för:", phone);
   // Här läggs anropet till Notification Service senare (K3)
});

// --- NINA: Översättningstjänst (K4) ---
function changeLanguage(lang) {
   console.log("Nina byter språk till:", lang);
   document.querySelector("h1").innerText = translations[lang].title;
}

// --- SAM: Autentisering (K6) ---
function loginWithBankID() {
   console.log("Sam anropar BankID-tjänsten...");
   // Här läggs Sams backend-logik in senare
}

// --- SONIA: Karttjänst (K2) ---
function initMap() {
   console.log("Sonia ritar ut kartan med koordinater:", mockSites);
   // Här integreras Google Maps eller Leaflet senare
}

// --- NINA: Betaltjänst (K5) ---
function processPayment() {
   console.log("Nina hanterar betalningen för prenumerationen");
}

// Körs när sidan laddas
window.onload = () => {
   initMap(); // Sonias del
   renderSites(mockSites); // Amandas del (frontend)
};
