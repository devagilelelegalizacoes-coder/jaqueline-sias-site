/* Botão flutuante de WhatsApp: exibe o tooltip "Fale diretamente comigo"
   uma vez por sessão em telas com mouse. Links são gerados no servidor
   (wa.me + número configurado em WHATSAPP_NUMBER). */
(() => {
  "use strict";
  const float = document.querySelector("[data-wa-float]");
  if (!float) return;

  const canHover = window.matchMedia("(hover: hover) and (min-width: 900px)").matches;
  if (!canHover) return;

  let seen = false;
  try { seen = sessionStorage.getItem("wa-tip-seen") === "1"; } catch (_) { /* armazenamento indisponível */ }
  if (seen) return;

  window.setTimeout(() => {
    float.classList.add("show-tip");
    window.setTimeout(() => float.classList.remove("show-tip"), 5000);
    try { sessionStorage.setItem("wa-tip-seen", "1"); } catch (_) { /* ignora */ }
  }, 3500);

  float.addEventListener("mouseenter", () => float.classList.remove("show-tip"));
})();
