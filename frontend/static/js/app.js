const API_BASE = "http://127.0.0.1:8000";

// MOCK som fallback om API:et inte svarar
const mockSites = [
   {
      name: "Örlogsstaden Karlskrona",
      description: "En välbevarad marinbas från 1600-talet.",
   },
   {
      name: "Hansestaden Visby",
      description: "En fantastisk medeltida ringmursstad.",
   },
];

const translations = {
   sv: { title: "Världsarv i din närhet" },
   en: { title: "World Heritage Sites Near You" },
};

// --- AMANDA: Renderingsfunktion ---
function renderSites(sites) {
   const container = document.getElementById("sites-display");
   if (!container) return;

   container.innerHTML = sites
      .map(
         (site) => `
         <div class="site-card">
             <h3>${site.name || site.title}</h3>
             <p>${site.description}</p>
         </div>
      `
      )
      .join("");
}

// --- SONIA: Hämta data från API ---
async function fetchSites() {
   try {
      const response = await fetch(`${API_BASE}/api/sites?radius=150`);
      if (!response.ok) throw new Error("API-fel");

      const sites = await response.json();
      renderSites(sites);

      // Skicka data till Sonias karta om funktionen finns
      if (typeof initMap === "function") {
         initMap(sites);
      }
   } catch (err) {
      console.error("Kunde inte hämta unesco-data, använder mock-data:", err);
      renderSites(mockSites); // Visar dummy-data om kollegans backend är nere
   }
}

// --- RIYAAQ & NINA: SMS & Betalning ---
const smsForm = document.getElementById("sms-form");
if (smsForm) {
   smsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const phone = document.getElementById("phone").value;
      const isSubscribed = document.getElementById("pay-confirm").checked;

      if (!isSubscribed) {
         alert("Du måste godkänna prenumerationen.");
         return;
      }

      try {
         // 1. Anropa Ninas Betaltjänst
         const payRes = await fetch(`${API_BASE}/payment/subscribe`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: "amanda_test", method: "swish" }),
         });

         if (payRes.ok) {
            // 2. Om betalning ok, anropa Riyaaqs SMS-tjänst
            const notifRes = await fetch(`${API_BASE}/notification/subscribe`, {
               method: "POST",
               headers: { "Content-Type": "application/json" },
               body: JSON.stringify({ user_id: "amanda_test", phone: phone }),
            });

            if (notifRes.ok) {
               alert("Tjänsten aktiverad! Du får nu SMS vid världsarv.");
            }
         }
      } catch (err) {
         console.error("Ett fel uppstod vid aktivering:", err);
      }
   });
}

// --- NINA: Översättningstjänst ---
async function changeLanguage(lang) {
   // Uppdatera huvudrubriken direkt från vårt lokala objekt (snabbare UX)
   if (translations[lang]) {
      document.querySelector("h1").innerText = translations[lang].title;
   }

   try {
      // Anropa Ninas backend för att översätta specifika sektioner (t.ex. "Lokala platser")
      const response = await fetch(`${API_BASE}/translation/translate`, {
         method: "POST",
         headers: { "Content-Type": "application/json" },
         body: JSON.stringify({
            text: "Lokala platser",
            target_language: lang,
         }),
      });
      const result = await response.json();
      document.querySelector("h2").innerText = result.translated_text;
   } catch (err) {
      console.error("Kunde inte hämta översättning från API:", err);
   }
}

// --- SAM: Autentisering ---
function loginWithBankID() {
   console.log("Sam anropar BankID-tjänsten via API:et...");
   // Här kan du lägga till fetch(`${API_BASE}/auth/bankid`) när Sam är redo
   alert("BankID-inloggning startad (Sams modul)");
}

// Starta appen när fönstret laddas
window.onload = () => {
   fetchSites();
};
