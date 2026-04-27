const modal = document.getElementById("unescoModal");
const openBtn = document.getElementById("openAdBtn");
const closeBtn = document.getElementById("closeAdBtn");
const bankidBtn = document.getElementById("bankidBtn");

openBtn.onclick = () => (modal.style.display = "block");
closeBtn.onclick = () => (modal.style.display = "none");

bankidBtn.onclick = function () {
  const phone = document.getElementById("phoneInput").value;
  if (phone.length < 5) {
    alert("Fyll i ditt mobilnummer först.");
    return;
  }
  bankidBtn.innerText = "Öppnar BankID...";
  setTimeout(() => {
    alert("Anrop skickas till Sams backend för legitimering.");
    bankidBtn.innerHTML = "Legitimera med BankID";
  }, 1500);
};

window.onclick = (event) => {
  if (event.target == modal) modal.style.display = "none";
};
