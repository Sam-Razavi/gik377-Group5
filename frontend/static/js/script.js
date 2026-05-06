// MODAL-HANTERING
const visitorModal = document.getElementById("unescoModal");
const memberModal = document.getElementById("memberModal");
const openBtn = document.getElementById("openAdBtn");
const closeAdBtn = document.getElementById("closeAdBtn");
const closeMemberBtn = document.getElementById("closeMemberBtn");
const toMemberLink = document.getElementById("toMemberView");

let lastFocusedElement;

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

// Öppna första modalen (Registrering)
openBtn.onclick = () => openModal(visitorModal);

// Stäng-knappar
closeAdBtn.onclick = () => closeModal(visitorModal);
closeMemberBtn.onclick = () => closeModal(memberModal);

// Växla till inloggad vy
toMemberLink.onclick = (e) => {
   e.preventDefault();
   visitorModal.style.display = "none";
   openModal(memberModal);
};

// CHATT-FUNKTIONALITET
document.getElementById("sendChat").onclick = () => {
   const input = document.getElementById("chatInput");
   const output = document.getElementById("chatOutput");
   if (input.value.trim()) {
      output.innerHTML += `<br><strong>Du:</strong> ${input.value}<br><strong>AI:</strong> Karlskrona är en unik örlogsstad med anor från 1600-talet...`;
      input.value = "";
      output.scrollTop = output.scrollHeight;
   }
};

// PRENUMERATION
function confirmCancel() {
   if (confirm("Är du säker på att du vill avsluta din prenumeration?")) {
      alert("Prenumeration avslutad.");
   }
}

// STÄNG VID KLICK UTANFÖR ELLER ESC
window.onclick = (e) => {
   if (e.target.classList.contains("modal-overlay")) {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
};

document.addEventListener("keydown", (e) => {
   if (e.key === "Escape") {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
});
