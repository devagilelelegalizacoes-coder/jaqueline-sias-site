/* Painel /admin: listas editáveis, contadores de SEO, prévias e confirmações. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));

  // ---------------------------------------------------------------- menu (celular)
  const menuBtn = $("[data-adm-menu]");
  const nav = $("[data-adm-nav]");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      menuBtn.setAttribute("aria-expanded", String(open));
    });
  }

  // ---------------------------------------------------------------- confirmações
  $$("form[data-confirm]").forEach((f) => {
    f.addEventListener("submit", (e) => {
      if (!window.confirm(f.dataset.confirm)) e.preventDefault();
    });
  });

  // ---------------------------------------------------------------- contadores de caracteres
  const updateCounter = (el) => {
    const out = $(`[data-counter-for="${el.id}"]`);
    if (!out) return;
    const n = el.value.trim().length;
    const min = Number(el.dataset.countMin);
    const max = Number(el.dataset.countMax);
    out.textContent = `${n} caracteres · ideal entre ${min} e ${max}`;
    out.classList.toggle("is-bad", n < min || n > max);
    out.classList.toggle("is-good", n >= min && n <= max);
  };
  $$("[data-count-min]").forEach((el) => {
    updateCounter(el);
    el.addEventListener("input", () => updateCounter(el));
  });

  // ---------------------------------------------------------------- prévia no Google
  $$("[data-serp]").forEach((serp) => {
    const card = serp.closest(".adm-card");
    const title = $('[data-preview-key="titulo"]', card);
    const desc = $('[data-preview-key="descricao"]', card);
    const cut = (s, n) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
    const sync = () => {
      if (title) $("[data-serp-title]", serp).textContent = cut(title.value, 62);
      if (desc) $("[data-serp-desc]", serp).textContent = cut(desc.value, 160);
    };
    [title, desc].forEach((el) => el && el.addEventListener("input", sync));
    sync();
  });

  // ---------------------------------------------------------------- ícones e cores
  const sprite = $("[data-icon-sprite]");
  const bindIcon = (sel) => {
    const preview = sel.parentElement.querySelector("[data-icon-preview]");
    sel.addEventListener("change", () => {
      const src = sprite && $(`[data-icon="${sel.value}"]`, sprite);
      if (preview) preview.innerHTML = src ? src.innerHTML : "";
    });
  };
  const bindColor = (input) => {
    const code = input.parentElement.querySelector("[data-color-code]");
    input.addEventListener("input", () => { if (code) code.textContent = input.value.toUpperCase(); });
  };
  $$("[data-icon-select]").forEach(bindIcon);
  $$('input[type="color"]').forEach(bindColor);

  // ---------------------------------------------------------------- listas (incluir, remover, ordenar)
  const renumber = (list) => {
    $$(":scope > [data-row]", list).forEach((row, i) => {
      const num = $("[data-row-num]", row);
      if (num) num.textContent = String(i + 1);
    });
  };
  const bindRow = (row) => {
    const firstInput = $(".lrow-body input[type=text], .lrow-body textarea", row);
    const title = $("[data-row-title]", row);
    if (firstInput && title) {
      firstInput.addEventListener("input", () => { title.textContent = firstInput.value || "Novo item"; });
    }
    $$("[data-icon-select]", row).forEach(bindIcon);
  };

  $$("[data-list]").forEach((list) => {
    renumber(list);
    $$(":scope > [data-row]", list).forEach(bindRow);

    list.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn || !list.contains(btn)) return;
      const row = btn.closest("[data-row]");
      if (!row) return;
      if (btn.hasAttribute("data-remove")) {
        e.preventDefault();
        const label = $("[data-row-title]", row)?.textContent || "este item";
        if (window.confirm(`Remover "${label}"? (A remoção só vale depois de salvar.)`)) {
          row.remove();
          renumber(list);
          markDirty();
        }
      } else if (btn.dataset.move) {
        e.preventDefault();
        if (btn.dataset.move === "up" && row.previousElementSibling) list.insertBefore(row, row.previousElementSibling);
        if (btn.dataset.move === "down" && row.nextElementSibling) list.insertBefore(row.nextElementSibling, row);
        renumber(list);
        btn.focus();
        markDirty();
      }
    });
  });

  let counter = 10000;
  $$("[data-list-add]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.listAdd;
      const list = $(`[data-list="${id}"]`);
      const tpl = $(`template[data-list-template="${id}"]`);
      const max = Number(list.dataset.max || 100);
      if ($$(":scope > [data-row]", list).length >= max) {
        window.alert(`Limite de ${max} itens.`);
        return;
      }
      const html = tpl.innerHTML.replaceAll("__i__", String(counter++));
      list.insertAdjacentHTML("beforeend", html);
      const row = list.lastElementChild;
      bindRow(row);
      renumber(list);
      markDirty();
      const first = $("input, textarea, select", $(".lrow-body", row));
      if (first) first.focus();
    });
  });

  // ---------------------------------------------------------------- prévia de fotos
  $$("[data-photo-input]").forEach((input) => {
    input.addEventListener("change", () => {
      const img = $(`[data-photo-preview="${input.name}"]`);
      const file = input.files && input.files[0];
      if (img && file) img.src = URL.createObjectURL(file);
    });
  });

  // ---------------------------------------------------------------- alterações não salvas
  const form = $("[data-edit-form]");
  let dirty = false;
  function markDirty() {
    dirty = true;
    const msg = $("[data-dirty-msg]");
    if (msg) msg.hidden = false;
  }
  if (form) {
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    form.addEventListener("submit", () => {
      dirty = false;
      // numera as linhas na ordem exibida para o servidor gravar na mesma ordem
      $$("[data-list]", form).forEach((list) => {
        $$(":scope > [data-row]", list).forEach((row, i) => {
          $$("[name]", row).forEach((el) => {
            el.name = el.name.replace(/^(l:[^:]+:)\d+(:)/, `$1${i}$2`);
          });
        });
      });
      const btn = $('button[type="submit"]', form);
      if (btn) { btn.disabled = true; btn.textContent = "Salvando…"; }
    });
    window.addEventListener("beforeunload", (e) => {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    });
  }
})();
