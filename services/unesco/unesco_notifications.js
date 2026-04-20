// Ansvarig: Sonia Tolouifar
// Modul: UNESCO-data & Karttjänst
// Notisfunktion — visar webbläsarnotis med närmaste världsarv vid sidladdning

function visaVarldsarvsNotis(site) {
   const titel = site.name_en || "Okänt världsarv";
   const avstand = site.distance_km;
   const text = `${titel} ligger ${avstand} km härifrån!`;

   if (!("Notification" in window)) {
      console.log("Webbläsaren stöder inte notiser.");
      return;
   }

   if (Notification.permission === "granted") {
      new Notification("Världsarv i närheten!", { body: text });
   } else if (Notification.permission !== "denied") {
      Notification.requestPermission().then((permission) => {
         if (permission === "granted") {
            new Notification("Världsarv i närheten!", { body: text });
         }
      });
   }
}

function hamtaNarmastVarldsarv() {
   if (!navigator.geolocation) {
      console.log("Geolokalisering stöds inte — använder Borlänge som standard.");
      hamtaMedBorlange();
      return;
   }

   navigator.geolocation.getCurrentPosition(
      (position) => {
         const lat = position.coords.latitude;
         const lon = position.coords.longitude;

         fetch(`/unesco/sites?lat=${lat}&lon=${lon}&radius=150`)
            .then((res) => res.json())
            .then((sites) => {
               if (sites.length > 0) {
                  visaVarldsarvsNotis(sites[0]);
               }
            })
            .catch((err) => console.error("Kunde inte hämta världsarvsdata:", err));
      },
      () => {
         console.log("Platsinformation nekades — använder Borlänge som standard.");
         hamtaMedBorlange();
      }
   );
}

function hamtaMedBorlange() {
   fetch("/unesco/sites?radius=150")
      .then((res) => res.json())
      .then((sites) => {
         if (sites.length > 0) {
            visaVarldsarvsNotis(sites[0]);
         }
      })
      .catch((err) => console.error("Kunde inte hämta världsarvsdata:", err));
}

// Körs automatiskt när scriptet laddas
hamtaNarmastVarldsarv();
