// MODAL-HANTERING
const visitorModal = document.getElementById("unescoModal");
const memberModal = document.getElementById("memberModal");
const openBtn = document.getElementById("openAdBtn");
const closeAdBtn = document.getElementById("closeAdBtn");
const closeMemberBtn = document.getElementById("closeMemberBtn");
const toMemberLink = document.getElementById("toMemberView");
const bankidBtn = document.getElementById("bankidBtn");

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

openBtn.onclick = () => openModal(visitorModal);
closeAdBtn.onclick = () => closeModal(visitorModal);
closeMemberBtn.onclick = () => closeModal(memberModal);

toMemberLink.onclick = (e) => {
   e.preventDefault();
   visitorModal.style.display = "none";
   openModal(memberModal);
};

// BankID demo-effekt
bankidBtn.onclick = () => {
    bankidBtn.innerText = "Öppnar BankID...";
    setTimeout(() => {
        alert("Anrop skickas till backend för legitimering.");
        bankidBtn.innerHTML = `<img src="https://upload.wikimedia.org/wikipedia/commons/4/4e/BankID_logo.svg" style="width:24px"> Bekräfta med BankID`;
    }, 1500);
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

function confirmCancel() {
   if (confirm("Är du säker på att du vill avsluta din prenumeration?")) {
      alert("Prenumeration avslutad.");
   }
}

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