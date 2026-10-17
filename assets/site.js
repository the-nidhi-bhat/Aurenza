/* ==========================================================================
   Aurenza — shared page behaviour + the identity layer.

   The identity layer is deliberately small and self-contained: accounts are
   kept in this browser (localStorage) with PBKDF2-SHA256 password digests,
   and the session is a signed-in marker with an expiry. It is a real
   credential check, not a cosmetic gate — but it is LOCAL: the browser is
   the only authority, so it is a demo identity layer, not server
   authentication. Swapping it for a server session means replacing the four
   methods on Aurenza and nothing else.
   ========================================================================== */
(() => {
  'use strict';

  const USERS_KEY = 'aurenza.users.v1';
  const SESSION_KEY = 'aurenza.session.v1';
  const ITERATIONS = 210000;                 // OWASP figure for PBKDF2-SHA256
  const TTL_REMEMBER = 12 * 60 * 60 * 1000;  // 12h in localStorage
  const TTL_SESSION = 2 * 60 * 60 * 1000;    // 2h in sessionStorage

  const hex = (buf) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
  const randomSalt = () => hex(crypto.getRandomValues(new Uint8Array(16)));

  async function digest(password, saltHex) {
    if (!(window.crypto && window.crypto.subtle)) throw new Error('This browser cannot hash passwords securely.');
    const salt = new Uint8Array(saltHex.match(/.{2}/g).map((h) => parseInt(h, 16)));
    const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits(
      { name: 'PBKDF2', salt, iterations: ITERATIONS, hash: 'SHA-256' }, key, 256);
    return hex(new Uint8Array(bits));
  }

  const users = () => {
    try { return JSON.parse(localStorage.getItem(USERS_KEY) || '{}'); } catch (e) { return {}; }
  };
  const saveUsers = (all) => localStorage.setItem(USERS_KEY, JSON.stringify(all));

  const normalise = (email) => String(email || '').trim().toLowerCase();
  const isEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);

  /* ---------- session ---------- */
  function current() {
    let raw = null;
    try { raw = localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY); }
    catch (e) { return null; }
    if (!raw) return null;
    let s;
    try { s = JSON.parse(raw); } catch (e) { return null; }
    if (!s || !s.email || !s.exp || s.exp < Date.now()) { signOut(); return null; }
    return s;
  }

  function writeSession(user, remember) {
    const session = {
      email: user.email,
      name: user.name,
      exp: Date.now() + (remember ? TTL_REMEMBER : TTL_SESSION),
    };
    const store = remember ? localStorage : sessionStorage;
    const other = remember ? sessionStorage : localStorage;
    try {
      other.removeItem(SESSION_KEY);
      store.setItem(SESSION_KEY, JSON.stringify(session));
    } catch (e) { /* storage blocked: the caller still gets a session object */ }
    return session;
  }

  function signOut() {
    try {
      localStorage.removeItem(SESSION_KEY);
      sessionStorage.removeItem(SESSION_KEY);
    } catch (e) { /* ignore */ }
  }

  /* ---------- sign up / in ---------- */
  async function signUp({ name, email, password, confirm }) {
    const clean = normalise(email);
    if (String(name || '').trim().length < 2) throw new Error('Please enter your name.');
    if (!isEmail(clean)) throw new Error('Please enter a valid email address.');
    if (String(password || '').length < 8) throw new Error('Your password needs at least 8 characters.');
    if (password !== confirm) throw new Error('Those passwords do not match.');
    const all = users();
    if (all[clean]) throw new Error('An account already exists for that email — sign in instead.');
    const salt = randomSalt();
    all[clean] = {
      name: String(name).trim(),
      email: clean,
      salt,
      hash: await digest(password, salt),
      iterations: 210000,
      createdAt: new Date().toISOString(),
    };
    saveUsers(all);
    return { name: all[clean].name, email: clean };
  }

  async function signIn({ email, password }) {
    const clean = normalise(email);
    const user = users()[clean];
    if (!user) throw new Error('No account found for that email.');
    const attempt = await digest(password, user.salt);
    if (attempt !== user.hash) throw new Error('That password is incorrect.');
    return { name: user.name, email: user.email };
  }

  /* Seed the demo account once, so the console is reachable in one click. */
  async function seedDemo() {
    const all = users();
    if (all['demo@aurenza.dev']) return false;
    const salt = randomSalt();
    all['demo@aurenza.dev'] = {
      name: 'Demo operator',
      email: 'demo@aurenza.dev',
      salt,
      hash: await digest('harvest-2026', salt),
      iterations: ITERATIONS,
      createdAt: new Date().toISOString(),
      demo: true,
    };
    saveUsers(all);
    return true;
  }

  /* Redirect anonymous visitors of a protected page. */
  function requireSession(next) {
    if (current()) return true;
    const target = next || window.location.pathname;
    window.location.replace('/signin/?next=' + encodeURIComponent(target));
    return false;
  }

  window.Aurenza = {
    seedDemo, signUp, signIn, signOut, current, requireSession,
    hashingIterations: 210000,
  };

  /* ---------- page wiring ---------- */
  const $ = (sel, root) => (root || document).querySelector(sel);

  function initThemeToggle() {
    const btn = $('#theme-toggle');
    if (!btn) return;
    const root = document.documentElement;
    const isDark = () => root.getAttribute('data-theme') === 'dark';
    const sync = () => {
      const dark = isDark();
      btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
      btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      btn.setAttribute('title', dark ? 'Light theme' : 'Dark theme');
    };
    sync();
    btn.addEventListener('click', () => {
      const next = isDark() ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('aurenza-theme', next); } catch (e) { /* ignore */ }
      sync();
    });
  }

  function initSessionUi() {
    const session = current();
    document.querySelectorAll('[data-session="user"]').forEach((el) => {
      if (!session) return;
      el.textContent = session.name;
      el.hidden = false;
    });
    document.querySelectorAll('[data-session="signed-out"]').forEach((el) => { el.hidden = !!session; });
    document.querySelectorAll('[data-session="signed-in"]').forEach((el) => { el.hidden = !session; });
    document.querySelectorAll('[data-session="console"]').forEach((link) => {
      link.setAttribute('href', session ? '/dashboard/' : '/signin/?next=%2Fdashboard%2F');
    });
    document.querySelectorAll('[data-signout]').forEach((el) => {
      el.addEventListener('click', (event) => {
        event.preventDefault();
        signOut();
        window.location.assign('/');
      });
    });
  }

  function showError(form, message) {
    const box = $('[data-auth-error]', form);
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
  }

  function setBusy(form, busy) {
    const btn = $('button[type="submit"]', form);
    if (btn) { btn.disabled = busy; btn.dataset.label = btn.dataset.label || btn.textContent; }
    if (btn) btn.textContent = busy ? 'Working…' : btn.dataset.label;
  }

  function initAuthForms() {
    const signin = $('[data-auth-form="signin"]');
    if (signin) {
      seedDemo();
      const fill = $('[data-demo-fill]');
      if (fill) {
        fill.addEventListener('click', () => {
          signin.elements.email.value = 'demo@aurenza.dev';
          signin.elements.password.value = 'harvest-2026';
          signin.elements.email.focus();
        });
      }
      signin.addEventListener('submit', async (event) => {
        event.preventDefault();
        showError(signin, '');
        setBusy(signin, true);
        try {
          const user = await signIn({
            email: signin.elements.email.value,
            password: signin.elements.password.value,
          });
          writeSession(user, signin.elements.remember.checked);
          const next = new URLSearchParams(window.location.search).get('next');
          window.location.assign(next && next.startsWith('/') ? next : '/dashboard/');
        } catch (err) {
          showError(signin, err.message);
          setBusy(signin, false);
        }
      });
    }

    const signup = $('[data-auth-form="signup"]');
    if (signup) {
      signup.addEventListener('submit', async (event) => {
        event.preventDefault();
        showError(signup, '');
        setBusy(signup, true);
        try {
          const user = await signUp({
            name: signup.elements.name.value,
            email: signup.elements.email.value,
            password: signup.elements.password.value,
            confirm: signup.elements.confirm.value,
          });
          writeSession(user, true);
          window.location.assign('/dashboard/');
        } catch (err) {
          showError(signup, err.message);
          setBusy(signup, false);
        }
      });
    }
  }

  /* Reveal animations are CSS-gated on html.js, so without an observer the page
     would stay invisible: either settle everything at once (reduced motion, no
     IntersectionObserver) or mark elements as they scroll in. */
  function initReveals() {
    const pending = document.querySelectorAll('.reveal:not(.is-in)');
    if (!pending.length) return;
    const calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (calm || !('IntersectionObserver' in window)) {
      pending.forEach((el) => el.classList.add('is-in'));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.01 });
    pending.forEach((el) => observer.observe(el));
  }

  document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initSessionUi();
    initAuthForms();
    initReveals();
  });
})();
