/* Jaqueline Sias Despachante — navegação, FAQ, avaliações e formulário de contato */
(() => {
  "use strict";
  document.documentElement.classList.add("js");

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Header: sombra ao rolar ---------- */
  const header = $("[data-header]");
  if (header) {
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- Menu mobile ---------- */
  const toggle = $("[data-menu-toggle]");
  const menu = $("[data-menu]");
  if (toggle && menu) {
    const setOpen = (open) => {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
      menu.hidden = !open;
      document.body.classList.toggle("menu-open", open);
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    menu.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") { setOpen(false); toggle.focus(); }
    });
    window.matchMedia("(min-width: 1080px)").addEventListener("change", (mq) => { if (mq.matches) setOpen(false); });
  }

  /* ---------- FAQ: acordeão (um item aberto por vez) ---------- */
  $$("[data-accordion]").forEach((group) => {
    const items = $$("details", group);
    items.forEach((item) => {
      item.addEventListener("toggle", () => {
        if (item.open) items.forEach((other) => { if (other !== item) other.open = false; });
      });
    });
  });

  /* ---------- Avaliações: mostrar mais / menos ---------- */
  const reviews = $("[data-reviews]");
  const reviewsBtn = $("[data-reviews-toggle]");
  if (reviews && reviewsBtn && $(".review-card--extra", reviews)) {
    reviews.classList.add("is-collapsed");
    reviewsBtn.hidden = false;
    reviewsBtn.addEventListener("click", () => {
      const collapsed = reviews.classList.toggle("is-collapsed");
      reviewsBtn.setAttribute("aria-expanded", String(!collapsed));
      reviewsBtn.textContent = collapsed ? reviewsBtn.dataset.labelMore : reviewsBtn.dataset.labelLess;
      if (collapsed) reviews.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  /* ---------- Formulário de contato ---------- */
  const form = $("[data-contact-form]");
  if (!form) return;

  const success = $("[data-form-success]");
  const alertBox = $("[data-form-alert]", form);
  const submitBtn = $("[data-submit]", form);
  const submitLabel = $("[data-submit-label]", form);

  // Pré-seleciona o serviço vindo de ?servico=
  const params = new URLSearchParams(window.location.search);
  const svc = params.get("servico");
  if (svc && form.servico && Array.from(form.servico.options).some((o) => o.value === svc)) form.servico.value = svc;

  // Máscara de telefone (XX) XXXXX-XXXX
  const phone = form.telefone;
  if (phone) {
    phone.addEventListener("input", () => {
      const d = phone.value.replace(/\D/g, "").slice(0, 11);
      let out = d;
      if (d.length > 2) out = `(${d.slice(0, 2)}) ${d.slice(2)}`;
      if (d.length > 6) out = `(${d.slice(0, 2)}) ${d.slice(2, d.length === 11 ? 7 : 6)}-${d.slice(d.length === 11 ? 7 : 6)}`;
      phone.value = out;
    });
  }

  const rules = {
    nome: (v) => (v.trim().length < 3 ? "Informe seu nome." : !/^[A-Za-zÀ-ÖØ-öø-ÿ' .-]+$/.test(v.trim()) ? "Use apenas letras no nome." : ""),
    telefone: (v) => { const d = v.replace(/\D/g, ""); return d.length < 10 || d.length > 11 ? "Informe um telefone com DDD." : ""; },
    mensagem: (v) => (v.trim().length < 10 ? "Escreva uma mensagem com pelo menos 10 caracteres." : ""),
    consent: (_v, el) => (!el.checked ? "É necessário concordar para enviarmos o retorno." : ""),
  };

  const setError = (name, msg) => {
    const field = form.elements[name];
    const err = $(`[data-error-for="${name}"]`, form);
    if (field) {
      if (msg) field.setAttribute("aria-invalid", "true");
      else field.removeAttribute("aria-invalid");
    }
    if (err) { err.textContent = msg || ""; err.hidden = !msg; }
  };

  const validate = () => {
    let first = null;
    Object.entries(rules).forEach(([name, rule]) => {
      const el = form.elements[name];
      if (!el) return;
      const msg = rule(el.value, el);
      setError(name, msg);
      if (msg && !first) first = el;
    });
    return first;
  };

  Object.keys(rules).forEach((name) => {
    const el = form.elements[name];
    if (!el) return;
    const evt = el.type === "checkbox" ? "change" : "blur";
    el.addEventListener(evt, () => { if (el.value || el.type === "checkbox") setError(name, rules[name](el.value, el)); });
    el.addEventListener("input", () => { if (el.getAttribute("aria-invalid") === "true") setError(name, rules[name](el.value, el)); });
  });

  const showAlert = (msg) => { if (!alertBox) return; alertBox.textContent = msg || ""; alertBox.hidden = !msg; };
  const setLoading = (on) => {
    submitBtn.disabled = on;
    submitBtn.setAttribute("aria-busy", String(on));
    submitLabel.textContent = on ? "Enviando…" : "Enviar mensagem";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showAlert("");
    const invalid = validate();
    if (invalid) { invalid.focus(); return; }

    setLoading(true);
    try {
      const res = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "fetch", Accept: "application/json" },
        credentials: "same-origin",
      });
      let data = {};
      try { data = await res.json(); } catch (_) { /* resposta não-JSON */ }

      if (res.ok && data.ok) {
        const name = $("[data-success-name]", success);
        if (name) name.textContent = data.first_name ? `, ${data.first_name}` : "";
        const wa = $("[data-success-wa]", success);
        if (wa) { if (data.wa) { wa.href = data.wa; wa.hidden = false; } else { wa.hidden = true; } }
        form.hidden = true;
        success.hidden = false;
        success.focus();
        form.reset();
        return;
      }
      if (data.errors) {
        Object.keys(rules).forEach((n) => setError(n, data.errors[n] || ""));
        const firstName = Object.keys(data.errors)[0];
        if (firstName && form.elements[firstName]) form.elements[firstName].focus();
      }
      showAlert(data.message || (data.errors ? "Revise os campos destacados." : "Não foi possível enviar agora. Tente novamente ou fale pelo WhatsApp."));
    } catch (_) {
      showAlert("Sem conexão no momento. Verifique sua internet ou fale pelo WhatsApp.");
    } finally {
      setLoading(false);
    }
  });

  const resetLink = $("[data-form-reset]", success);
  if (resetLink) {
    resetLink.addEventListener("click", (e) => {
      e.preventDefault();
      success.hidden = true;
      form.hidden = false;
      Object.keys(rules).forEach((n) => setError(n, ""));
      form.nome.focus();
    });
  }
})();
