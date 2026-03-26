/* ═══════════════════════════════════════════════════════════
   LogiCarga — app.js  |  Animaciones y mejoras globales
═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

  // ── 1. Auto-ocultar flash messages ──────────────────────
  const flashes = document.querySelectorAll('.flash, .lc-flash');
  flashes.forEach((el, i) => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s, transform 0.5s, max-height 0.5s';
      el.style.opacity = '0';
      el.style.transform = 'translateX(10px)';
      setTimeout(() => el.remove(), 500);
    }, 4000 + i * 200);
  });

  // ── 2. Sidebar: marcar activo con animación ──────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ── 3. Scroll reveal para cards ─────────────────────────
  const revealEls = document.querySelectorAll('.card, .stat, .perfil-card');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(18px)';
      el.style.transition = `opacity 0.45s ease ${i * 0.06}s, transform 0.45s ease ${i * 0.06}s`;
      io.observe(el);
    });
  }

  // ── 4. Topbar: efecto al hacer scroll ───────────────────
  const topbar = document.querySelector('.topbar');
  if (topbar) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 10) {
        topbar.style.boxShadow = '0 2px 24px rgba(120,53,15,0.12)';
        topbar.style.borderBottomColor = 'rgba(245,158,11,0.15)';
      } else {
        topbar.style.boxShadow = '';
        topbar.style.borderBottomColor = '';
      }
    }, { passive: true });
  }

  // ── 5. Ripple efecto en botones ─────────────────────────
  document.querySelectorAll('button[type="submit"], .btn-auth, .lc-btn-submit').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const ripple = document.createElement('span');
      const rect   = this.getBoundingClientRect();
      const size   = Math.max(rect.width, rect.height);
      ripple.style.cssText = `
        position:absolute; border-radius:50%;
        width:${size}px; height:${size}px;
        left:${e.clientX - rect.left - size/2}px;
        top:${e.clientY - rect.top  - size/2}px;
        background:rgba(255,255,255,0.25);
        transform:scale(0); animation:rippleAnim 0.5s ease-out forwards;
        pointer-events:none;
      `;
      if (!this.style.position || this.style.position === 'static') {
        this.style.position = 'relative';
      }
      this.style.overflow = 'hidden';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 500);
    });
  });

  // ── 6. Contadores animados en stats ─────────────────────
  const statNums = document.querySelectorAll('.stat p');
  statNums.forEach(el => {
    const target = parseInt(el.textContent, 10);
    if (!isNaN(target) && target > 0) {
      animateCount(el, 0, target, 900);
    }
  });

  function animateCount(el, from, to, duration) {
    const start = performance.now();
    const original = el.textContent;
    requestAnimationFrame(function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(tick);
      else el.textContent = original; // Restaura formato original
    });
  }

  // ── 7. Tablas: filas con delay de entrada ───────────────
  document.querySelectorAll('tbody tr').forEach((row, i) => {
    row.style.opacity = '0';
    row.style.transform = 'translateX(-8px)';
    row.style.transition = `opacity 0.3s ease ${i * 0.04}s, transform 0.3s ease ${i * 0.04}s`;
    setTimeout(() => {
      row.style.opacity = '1';
      row.style.transform = 'translateX(0)';
    }, 50 + i * 40);
  });

  // ── 8. Inputs: focus ring animado ───────────────────────
  document.querySelectorAll('input, select, textarea').forEach(input => {
    input.addEventListener('focus', function () {
      this.parentElement?.classList.add('input-focused');
    });
    input.addEventListener('blur', function () {
      this.parentElement?.classList.remove('input-focused');
    });
  });

  // ── 9. Inject ripple keyframe ────────────────────────────
  if (!document.getElementById('rippleStyle')) {
    const style = document.createElement('style');
    style.id = 'rippleStyle';
    style.textContent = `
      @keyframes rippleAnim {
        to { transform: scale(2.5); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  // ── 10. Sidebar mini-tooltip on collapsed ────────────────
  // (para pantallas medianas en el futuro)

  // ── 11. Título de página dinámico en topbar ──────────────
  const pageLabel = document.querySelector('.topbar-page-label');
  const pageH2 = document.querySelector('.page-header h2');
  if (pageLabel && pageH2 && !pageLabel.textContent.trim()) {
    pageLabel.textContent = pageH2.textContent;
  }

  // ── 12. Barra de progreso al cargar página ───────────────
  createPageProgressBar();

  function createPageProgressBar() {
    const bar = document.createElement('div');
    bar.style.cssText = `
      position:fixed; top:0; left:0; height:2px; z-index:9999;
      background:linear-gradient(90deg,#f59e0b,#fbbf24,#f59e0b);
      background-size:200%;
      animation:progressBar 0.8s ease-out forwards, shimmerBar 1.2s linear infinite;
      pointer-events:none;
    `;
    document.body.appendChild(bar);
    const style = document.createElement('style');
    style.textContent = `
      @keyframes progressBar {
        from { width:0; opacity:1; }
        to   { width:100%; opacity:0; }
      }
      @keyframes shimmerBar {
        0%   { background-position:200% 0; }
        100% { background-position:-200% 0; }
      }
    `;
    document.head.appendChild(style);
    setTimeout(() => bar.remove(), 900);
  }

});

// ── SIDEBAR USER CARD — click para abrir/cerrar ──────────────
(function () {
  const trigger = document.getElementById('sfUserTrigger');
  const card    = document.getElementById('sfHoverCard');
  const chevron = trigger ? trigger.querySelector('.sf-chevron') : null;
  if (!trigger || !card) return;

  let open = false;

  function openCard() {
    open = true;
    card.style.opacity       = '1';
    card.style.pointerEvents = 'all';
    card.style.transform     = 'translateY(0) scale(1)';
    trigger.style.background = 'rgba(251,191,36,0.10)';
    if (chevron) chevron.style.transform = 'rotate(180deg)';
  }
  function closeCard() {
    open = false;
    card.style.opacity       = '0';
    card.style.pointerEvents = 'none';
    card.style.transform     = 'translateY(8px) scale(0.97)';
    trigger.style.background = '';
    if (chevron) chevron.style.transform = '';
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    open ? closeCard() : openCard();
  });

  // Cerrar al hacer clic fuera
  document.addEventListener('click', (e) => {
    if (open && !card.contains(e.target) && !trigger.contains(e.target)) {
      closeCard();
    }
  });
  // Cerrar con Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && open) closeCard();
  });
})();

// ── TOPBAR PROFILE PILL — glow effect on hover ──────────────
(function () {
  const pill = document.querySelector('.topbar-profile-pill');
  if (!pill) return;
  pill.addEventListener('mouseenter', () => {
    pill.style.boxShadow = '0 0 0 3px rgba(245,158,11,0.18), 0 6px 24px rgba(120,53,15,0.18)';
  });
  pill.addEventListener('mouseleave', () => {
    pill.style.boxShadow = '';
  });
})();

// ── CURSOR GLOW — efecto sutil en toda la app ────────────────
(function () {
  if (window.innerWidth < 768) return; // Solo desktop
  const glow = document.createElement('div');
  glow.style.cssText = `
    position:fixed; width:300px; height:300px; border-radius:50%;
    background:radial-gradient(circle, rgba(245,158,11,0.04) 0%, transparent 70%);
    pointer-events:none; z-index:0; transform:translate(-50%,-50%);
    transition:left 0.4s ease, top 0.4s ease;
  `;
  document.body.appendChild(glow);
  document.addEventListener('mousemove', e => {
    glow.style.left = e.clientX + 'px';
    glow.style.top  = e.clientY + 'px';
  });
})();

// ── SMOOTH NUMBER COUNT para tablas de reportes ──────────────
(function() {
  const tds = document.querySelectorAll('.td-price, .td-km');
  tds.forEach((td, i) => {
    td.style.opacity = '0';
    td.style.transform = 'translateX(10px)';
    setTimeout(() => {
      td.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      td.style.opacity = '1';
      td.style.transform = 'translateX(0)';
    }, 200 + i * 60);
  });
})();

// ── NAV ITEMS — efecto de entrada en sidebar ─────────────────
(function () {
  const items = document.querySelectorAll('.nav-item');
  items.forEach((item, i) => {
    item.style.opacity = '0';
    item.style.transform = 'translateX(-12px)';
    setTimeout(() => {
      item.style.transition = `opacity 0.35s ease ${i * 0.04}s, transform 0.35s ease ${i * 0.04}s`;
      item.style.opacity = '1';
      item.style.transform = 'translateX(0)';
    }, 80);
  });
})();

// ── TOPBAR — fade in desde arriba ───────────────────────────
(function () {
  const topbar = document.querySelector('.topbar');
  if (!topbar) return;
  topbar.style.opacity = '0';
  topbar.style.transform = 'translateY(-8px)';
  setTimeout(() => {
    topbar.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    topbar.style.opacity = '1';
    topbar.style.transform = 'translateY(0)';
  }, 100);
})();


// ── LOGO PREMIUM — shimmer + wheel spin al hover ─────────────
(function () {
  // Agregar el div shimmer a cada logo
  document.querySelectorAll('.lc-logo-icon-wrap').forEach(wrap => {
    const shimmer = document.createElement('span');
    shimmer.className = 'lc-logo-shimmer';
    wrap.appendChild(shimmer);

    // Ruedas que giran al hover
    const wheels = wrap.querySelectorAll('circle[r="3"]');
    let wheelAnim = null;

    wrap.closest('a')?.addEventListener('mouseenter', () => {
      let angle = 0;
      wheelAnim = setInterval(() => {
        angle += 18;
        // Animar tuercas de cada rueda girando
        wrap.querySelectorAll('.lc-truck-svg').forEach(svg => {
          // Rotar todo el SVG ligeramente al hover ya lo maneja CSS
        });
      }, 30);
    });

    wrap.closest('a')?.addEventListener('mouseleave', () => {
      clearInterval(wheelAnim);
    });
  });

  // Efecto pulse en el logo grande del login
  const lgLogo = document.querySelector('.lc-logo-lg');
  if (lgLogo) {
    let bounceAnim;
    const startBounce = () => {
      let t = 0;
      bounceAnim = setInterval(() => {
        t += 0.05;
        const y = Math.sin(t) * 3;
        lgLogo.style.transform = `translateY(${y}px)`;
      }, 16);
    };
    // Solo animar cuando está visible
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) startBounce();
        else clearInterval(bounceAnim);
      });
    });
    obs.observe(lgLogo);
  }
})();

/* ═══════════════════════════════════════════════════════════
   LogiCarga — MEJORAS PREMIUM v22
═══════════════════════════════════════════════════════════ */

// ── TOAST GLOBAL mejorado ─────────────────────────────────────
window.lcToast = function(msg, type = 'success', duration = 3500) {
  const colors = {
    success: { bg:'linear-gradient(135deg,#059669,#065f46)', icon:'✅' },
    error:   { bg:'linear-gradient(135deg,#dc2626,#991b1b)', icon:'❌' },
    info:    { bg:'linear-gradient(135deg,#2563eb,#1e40af)', icon:'ℹ️' },
    warning: { bg:'linear-gradient(135deg,#d97706,#b45309)', icon:'⚠️' },
  };
  const c = colors[type] || colors.success;
  const t = document.createElement('div');
  t.innerHTML = `<span style="font-size:15px">${c.icon}</span> ${msg}`;
  t.style.cssText = `
    position:fixed; bottom:28px; left:50%; z-index:99999;
    transform:translateX(-50%) translateY(20px);
    background:${c.bg};
    color:white; font-size:13.5px; font-weight:700; font-family:'Sora',sans-serif;
    padding:14px 26px; border-radius:16px;
    box-shadow:0 8px 40px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.1);
    display:flex; align-items:center; gap:10px;
    opacity:0; transition:all 0.38s cubic-bezier(.34,1.56,.64,1);
    max-width:90vw; text-align:center; pointer-events:none;
    backdrop-filter:blur(10px);
  `;
  document.body.appendChild(t);
  requestAnimationFrame(() => {
    t.style.opacity = '1';
    t.style.transform = 'translateX(-50%) translateY(0)';
  });
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateX(-50%) translateY(12px)';
    setTimeout(() => t.remove(), 400);
  }, duration);
};

// ── RIPPLE en TODOS los botones ───────────────────────────────
document.addEventListener('click', function(e) {
  const btn = e.target.closest('button, .btn-iniciar, .btn-finalizar, .mf-confirm-green, .mf-confirm-blue, .lp-btn');
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.5;
  const ripple = document.createElement('span');
  ripple.style.cssText = `
    position:absolute; border-radius:50%; pointer-events:none;
    width:${size}px; height:${size}px;
    left:${e.clientX - rect.left - size/2}px;
    top:${e.clientY - rect.top - size/2}px;
    background:rgba(255,255,255,0.28);
    transform:scale(0); animation:lcRipple 0.55s ease-out forwards;
  `;
  if (getComputedStyle(btn).position === 'static') btn.style.position = 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}, { passive: true });

// Inyectar keyframe ripple
(function(){
  if (document.getElementById('lcRippleKF')) return;
  const s = document.createElement('style');
  s.id = 'lcRippleKF';
  s.textContent = '@keyframes lcRipple { to { transform:scale(2.2); opacity:0; } }';
  document.head.appendChild(s);
})();

// ── SCROLL SUAVE a anclas ─────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', function(e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior:'smooth', block:'start' }); }
  });
});

// ── TABLA: ordenar columnas al hacer click en header ──────────
document.querySelectorAll('table').forEach(table => {
  const headers = table.querySelectorAll('thead th');
  headers.forEach((th, colIdx) => {
    th.style.cursor = 'pointer';
    th.style.userSelect = 'none';
    th.title = 'Click para ordenar';
    let asc = true;
    th.addEventListener('click', () => {
      const tbody = table.querySelector('tbody');
      if (!tbody) return;
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {
        const aT = (a.cells[colIdx]?.textContent || '').trim();
        const bT = (b.cells[colIdx]?.textContent || '').trim();
        const aN = parseFloat(aT.replace(/[^0-9.-]/g,''));
        const bN = parseFloat(bT.replace(/[^0-9.-]/g,''));
        if (!isNaN(aN) && !isNaN(bN)) return asc ? aN - bN : bN - aN;
        return asc ? aT.localeCompare(bT,'es') : bT.localeCompare(aT,'es');
      });
      asc = !asc;
      headers.forEach(h => h.textContent = h.textContent.replace(/ [↑↓]$/, ''));
      th.textContent += asc ? ' ↓' : ' ↑';
      rows.forEach(r => tbody.appendChild(r));
    });
  });
});

// ── CONFIRM DIALOGS mejorados ─────────────────────────────────
window.lcConfirm = function(msg, onConfirm) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position:fixed; inset:0; z-index:99998; display:flex;
    align-items:center; justify-content:center; padding:20px;
    background:rgba(10,5,0,0.7); backdrop-filter:blur(8px);
    animation:fadeIn 0.2s ease;
  `;
  overlay.innerHTML = `
    <div style="
      background:#fff; border-radius:22px; padding:32px 36px; max-width:420px; width:100%;
      box-shadow:0 40px 100px rgba(0,0,0,0.4); text-align:center;
      animation:slideUp 0.3s cubic-bezier(.34,1.56,.64,1);
    ">
      <div style="width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,#fef3c7,#fde68a);
        display:flex;align-items:center;justify-content:center;margin:0 auto 18px;font-size:24px;">⚠️</div>
      <p style="font-size:15px;font-weight:700;color:#1c1009;margin:0 0 24px;line-height:1.5;">${msg}</p>
      <div style="display:flex;gap:10px;justify-content:center;">
        <button id="lcCancelBtn" style="
          flex:1;padding:12px;border-radius:12px;border:1.5px solid #f0ddb8;
          background:white;font-size:13px;font-weight:700;color:#8a7060;cursor:pointer;
          box-shadow:none;
        ">Cancelar</button>
        <button id="lcConfirmBtn" style="
          flex:1;padding:12px;border-radius:12px;
          background:linear-gradient(135deg,#f59e0b,#d97706);
          color:white;font-size:13px;font-weight:800;cursor:pointer;
          box-shadow:0 4px 16px rgba(217,119,6,0.35);
        ">Confirmar</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  const close = () => {
    overlay.style.opacity = '0';
    setTimeout(() => overlay.remove(), 200);
  };
  overlay.querySelector('#lcCancelBtn').onclick = close;
  overlay.querySelector('#lcConfirmBtn').onclick = () => { close(); onConfirm(); };
  overlay.onclick = e => { if (e.target === overlay) close(); };
  // Inyectar keyframes
  if (!document.getElementById('lcConfirmKF')) {
    const s = document.createElement('style');
    s.id = 'lcConfirmKF';
    s.textContent = `
      @keyframes fadeIn { from{opacity:0} to{opacity:1} }
      @keyframes slideUp { from{opacity:0;transform:translateY(24px)scale(0.95)} to{opacity:1;transform:none} }
    `;
    document.head.appendChild(s);
  }
};

// ── COUNTER ANIMADO para KPIs de dashboard ──────────────────
(function() {
  function animNum(el, final) {
    const isPrice = final > 10000;
    const duration = 1200;
    const start = performance.now();
    requestAnimationFrame(function tick(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const current = Math.round(eased * final);
      if (isPrice) {
        el.textContent = '$' + current.toLocaleString('es-CO');
      } else {
        el.textContent = current.toLocaleString('es-CO');
      }
      if (p < 1) requestAnimationFrame(tick);
    });
  }

  // Observar cuando los stat values entren al viewport
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const raw = el.textContent.replace(/[^0-9]/g, '');
      const num = parseInt(raw);
      if (!isNaN(num) && num > 0) animNum(el, num);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.db-stat-value, .mv-stat .sv, .modal-kpi-num').forEach(el => {
    observer.observe(el);
  });
})();

// ── KEYBOARD SHORTCUT: Ctrl+K para buscar ────────────────────
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const firstInput = document.querySelector('input[type="text"], input[type="search"], input[type="email"]');
    if (firstInput) { firstInput.focus(); firstInput.select(); }
  }
});

// ── AUTO-FORMATEAR campos de peso/moneda mientras se escribe ─
document.querySelectorAll('input[name*="costo"], input[name*="valor"], input[name*="monto"]').forEach(inp => {
  inp.addEventListener('blur', function() {
    const val = parseFloat(this.value.replace(/[^0-9.]/g,''));
    if (!isNaN(val) && val > 0) {
      // Solo agregar separadores de miles en el placeholder visual
      this.dataset.formatted = val.toLocaleString('es-CO');
    }
  });
});

// ── INDICADOR DE CARGA en formularios ────────────────────────
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function() {
    const submitBtn = this.querySelector('button[type="submit"]');
    if (submitBtn && !submitBtn.dataset.noLoader) {
      submitBtn.dataset.originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 0.8s linear infinite;display:inline-block">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Guardando...`;
      submitBtn.disabled = true;
      submitBtn.style.opacity = '0.85';
      // Restaurar si hay error (3 segundos fallback)
      setTimeout(() => {
        if (submitBtn.disabled) {
          submitBtn.innerHTML = submitBtn.dataset.originalText || 'Enviar';
          submitBtn.disabled = false;
          submitBtn.style.opacity = '';
        }
      }, 8000);
    }
  });
});

// Keyframe spin
(function(){
  if (document.getElementById('lcSpinKF')) return;
  const s = document.createElement('style');
  s.id = 'lcSpinKF';
  s.textContent = '@keyframes spin { to { transform:rotate(360deg); } }';
  document.head.appendChild(s);
})();

