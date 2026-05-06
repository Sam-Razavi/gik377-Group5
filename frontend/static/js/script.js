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
   // Flytta fokus till stäng-knappen inuti modalen
   modal.querySelector(".close-modal").focus();
}

function closeModal(modal) {
   modal.style.display = "none";
   document.body.style.overflow = "auto";
   // Återställ fokus till knappen som öppnade modalen
   if (lastFocusedElement) lastFocusedElement.focus();
}

openBtn.onclick = () => openModal(visitorModal);

closeAdBtn.onclick = () => closeModal(visitorModal);
closeMemberBtn.onclick = () => closeModal(memberModal);

toMemberLink.onclick = (e) => {
   e.preventDefault();
   visitorModal.style.display = "none";
   openModal(memberModal);
};

// AI-Chat simulering med aria-live stöd (via HTML)
document.getElementById("sendChat").onclick = () => {
   const input = document.getElementById("chatInput");
   const output = document.getElementById("chatOutput");
   if (input.value) {
      output.innerHTML += `<br><strong>Du:</strong> ${input.value}<br><strong>AI:</strong> Karlskrona är en unik örlogsstad...`;
      input.value = "";
      output.scrollTop = output.scrollHeight;
   }
};

function confirmCancel() {
   if (confirm("Är du säker på att du vill avsluta din prenumeration?")) {
      alert("Prenumeration avslutad.");
   }
}

// Stäng vid klick utanför
window.onclick = (e) => {
   if (e.target.classList.contains("modal-overlay")) {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
};

// Stäng med Escape-tangenten
document.addEventListener("keydown", (e) => {
   if (e.key === "Escape") {
      closeModal(visitorModal);
      closeModal(memberModal);
   }
});
