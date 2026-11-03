/* Revelação suave de elementos ao rolar. Respeita "reduzir movimento" e nunca
   esconde o que já está visível no carregamento (sem piscar, sem impacto no LCP). */
(() => {
  "use strict";
  if (!("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const items = Array.from(document.querySelectorAll(".reveal"));
  if (!items.length) return;

  const viewportH = window.innerHeight || document.documentElement.clientHeight;
  const pending = items.filter((el) => el.getBoundingClientRect().top > viewportH * 0.92);

  // Pequeno escalonamento entre irmãos (cartões em grade)
  pending.forEach((el) => {
    const siblings = Array.from(el.parentElement.children).filter((c) => c.classList.contains("reveal"));
    const i = siblings.indexOf(el);
    el.style.setProperty("--reveal-delay", `${Math.min(i, 5) * 70}ms`);
    el.classList.add("reveal--pending");
  });

  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      el.classList.remove("reveal--pending");
      el.classList.add("reveal--in");
      el.addEventListener("animationend", () => el.classList.remove("reveal--in"), { once: true });
      io.unobserve(el);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  pending.forEach((el) => io.observe(el));

  // Impressão / salvar como PDF: mostra tudo
  window.addEventListener("beforeprint", () => {
    pending.forEach((el) => el.classList.remove("reveal--pending"));
    io.disconnect();
  });
})();
