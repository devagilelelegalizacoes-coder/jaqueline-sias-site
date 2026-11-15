/* Pixels e análise configurados no painel /admin.
   - Só carrega depois do consentimento (LGPD), quando o aviso de cookies está ativo.
   - Registra conversões: clique no WhatsApp e envio do formulário. */
(() => {
  "use strict";
  const cfgEl = document.getElementById("tracking-config");
  if (!cfgEl) return;
  let cfg;
  try { cfg = JSON.parse(cfgEl.textContent); } catch (_) { return; }

  const KEY = "cookie-consent-v1";
  const getChoice = () => { try { return localStorage.getItem(KEY); } catch (_) { return null; } };
  const setChoice = (v) => { try { localStorage.setItem(KEY, v); } catch (_) { /* sem armazenamento */ } };

  const w = window;
  const d = document;
  let loaded = false;

  const addScript = (src) => {
    const s = d.createElement("script");
    s.async = true;
    s.src = src;
    d.head.appendChild(s);
    return s;
  };

  // Executa o código personalizado guardado em <template> (scripts precisam ser recriados).
  const runCustom = (id, target) => {
    const tpl = d.getElementById(id);
    if (!tpl) return;
    Array.from(tpl.content.childNodes).forEach((node) => {
      if (node.nodeName === "SCRIPT") {
        const s = d.createElement("script");
        Array.from(node.attributes).forEach((a) => s.setAttribute(a.name, a.value));
        s.text = node.textContent;
        target.appendChild(s);
      } else {
        target.appendChild(node.cloneNode(true));
      }
    });
  };

  const load = () => {
    if (loaded) return;
    loaded = true;

    // Google Analytics 4 / Google Ads (gtag.js)
    const gtagIds = [cfg.ga4, cfg.ads].filter(Boolean);
    if (gtagIds.length) {
      w.dataLayer = w.dataLayer || [];
      w.gtag = function gtag() { w.dataLayer.push(arguments); };
      w.gtag("js", new Date());
      gtagIds.forEach((id) => w.gtag("config", id));
      addScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gtagIds[0])}`);
    }

    // Google Tag Manager
    if (cfg.gtm) {
      w.dataLayer = w.dataLayer || [];
      w.dataLayer.push({ "gtm.start": Date.now(), event: "gtm.js" });
      addScript(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(cfg.gtm)}`);
    }

    // Pixel da Meta
    if (cfg.meta && !w.fbq) {
      const n = (w.fbq = function fbq() {
        if (n.callMethod) n.callMethod.apply(n, arguments); else n.queue.push(arguments);
      });
      if (!w._fbq) w._fbq = n;
      n.push = n; n.loaded = true; n.version = "2.0"; n.queue = [];
      addScript("https://connect.facebook.net/en_US/fbevents.js");
      w.fbq("init", cfg.meta);
      w.fbq("track", "PageView");
    }

    // Pixel do TikTok
    if (cfg.tiktok && !w.ttq) {
      w.TiktokAnalyticsObject = "ttq";
      const ttq = (w.ttq = w.ttq || []);
      ttq.methods = ["page", "track", "identify", "instances", "debug", "on", "off", "once", "ready", "alias",
        "group", "enableCookie", "disableCookie", "holdConsent", "revokeConsent", "grantConsent"];
      ttq.setAndDefer = (t, e) => { t[e] = function () { t.push([e].concat(Array.prototype.slice.call(arguments, 0))); }; };
      ttq.methods.forEach((m) => ttq.setAndDefer(ttq, m));
      ttq.instance = (t) => { const e = ttq._i[t] || []; ttq.methods.forEach((m) => ttq.setAndDefer(e, m)); return e; };
      ttq.load = (id, opts) => {
        const url = "https://analytics.tiktok.com/i18n/pixel/events.js";
        ttq._i = ttq._i || {}; ttq._i[id] = []; ttq._i[id]._u = url;
        ttq._t = ttq._t || {}; ttq._t[id] = +new Date();
        ttq._o = ttq._o || {}; ttq._o[id] = opts || {};
        addScript(`${url}?sdkid=${encodeURIComponent(id)}&lib=ttq`);
      };
      ttq.load(cfg.tiktok);
      ttq.page();
    }

    // Microsoft Clarity
    if (cfg.clarity && !w.clarity) {
      w.clarity = function clarity() { (w.clarity.q = w.clarity.q || []).push(arguments); };
      addScript(`https://www.clarity.ms/tag/${encodeURIComponent(cfg.clarity)}`);
    }

    runCustom("custom-code-head", d.head);
    runCustom("custom-code-body", d.body);

    // Envio do formulário sem JavaScript (página recarregada com a mensagem de sucesso)
    if (d.querySelector("[data-contact-sent]")) track("lead");
  };

  // ------------------------------------------------------------ conversões
  function track(kind) {
    if (!loaded) return;
    const lead = kind === "lead";
    if (w.gtag) {
      w.gtag("event", lead ? "generate_lead" : "contact", { method: lead ? "formulario" : "whatsapp" });
      if (cfg.ads && cfg.adsLabel) w.gtag("event", "conversion", { send_to: `${cfg.ads}/${cfg.adsLabel}` });
    }
    if (cfg.gtm && w.dataLayer) w.dataLayer.push({ event: lead ? "form_submit_lead" : "whatsapp_click" });
    if (w.fbq) w.fbq("track", lead ? "Lead" : "Contact");
    if (w.ttq) w.ttq.track(lead ? "SubmitForm" : "Contact");
  }

  d.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest('a[href^="https://wa.me/"]');
    if (a) track("whatsapp");
  }, true);
  d.addEventListener("contact:sent", () => track("lead"));

  // ------------------------------------------------------------ consentimento
  const banner = d.querySelector("[data-cookie-banner]");
  const showBanner = () => { if (banner) banner.hidden = false; };
  const hideBanner = () => { if (banner) banner.hidden = true; };

  if (!cfg.consent) {
    load();
  } else {
    const choice = getChoice();
    if (choice === "granted") load();
    else if (choice !== "denied") showBanner();
  }

  d.addEventListener("click", (e) => {
    const t = e.target;
    if (!t.closest) return;
    if (t.closest("[data-cookie-accept]")) { setChoice("granted"); hideBanner(); load(); }
    else if (t.closest("[data-cookie-reject]")) {
      const wasGranted = getChoice() === "granted";
      setChoice("denied");
      hideBanner();
      if (wasGranted) w.location.reload(); // descarrega os pixels já ativos
    } else if (t.closest("[data-cookie-prefs]")) showBanner();
  });
})();
