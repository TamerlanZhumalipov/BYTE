(() => {
  const panel = document.querySelector('[data-cookie-panel]');
  if (!panel) return;
  const key = 'byte-privacy-choice';
  const version = panel.dataset.version;
  const lifetime = 180 * 24 * 60 * 60 * 1000;
  const kk = document.documentElement.lang === 'kk';
  let choice = null;
  let returnFocus = null;
  let expiryTimer;
  function readChoice() {
    try {
      const value = JSON.parse(localStorage.getItem(key));
      if (value && value.version === version && typeof value.media === 'boolean'
          && Number.isFinite(value.at) && value.at <= Date.now() && Date.now() - value.at < lifetime) return value;
      localStorage.removeItem(key);
    } catch (_) { /* No persistent permission when storage is unavailable. */ }
    return null;
  }
  function syncMedia() {
    document.querySelectorAll('[data-external-video]').forEach((wrapper) => {
      const placeholder = wrapper.querySelector('[data-media-placeholder]');
      const existing = wrapper.querySelector('iframe');
      if (choice?.media && !existing) {
        const source = wrapper.dataset.externalVideo;
        let url;
        try { url = new URL(source, location.origin); } catch (_) { return; }
        if (!['https:', 'http:'].includes(url.protocol)) return;
        const frame = document.createElement('iframe');
        frame.title = wrapper.dataset.videoTitle || 'Video';
        frame.src = url.href;
        frame.loading = 'lazy';
        frame.referrerPolicy = 'strict-origin-when-cross-origin';
        frame.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture';
        frame.allowFullscreen = true;
        wrapper.appendChild(frame);
      } else if (!choice?.media && existing) {
        existing.remove();
      }
      placeholder.hidden = !!choice?.media;
    });
  }
  function sync() {
    syncMedia();
    panel.querySelector('[data-cookie-current]').textContent = choice
      ? (choice.media ? (kk ? 'Қазір: сыртқы видеоға рұқсат берілген.' : 'Сейчас: внешние видео разрешены.')
        : (kk ? 'Қазір: тек қажетті сақтау.' : 'Сейчас: только необходимое хранение.')) : '';
    panel.querySelector('[data-cookie-close]').hidden = !choice;
    clearTimeout(expiryTimer);
    if (choice) {
      // Browsers cap setTimeout to a signed 32-bit integer.
      expiryTimer = setTimeout(() => { choice = readChoice(); sync(); if (!choice) panel.hidden = false; },
        Math.min(choice.at + lifetime - Date.now() + 1, 2147483647));
    }
  }
  function openPanel(trigger) {
    returnFocus = trigger;
    panel.hidden = false;
    panel.focus();
  }
  function closePanel() {
    panel.hidden = true;
    if (returnFocus?.isConnected) returnFocus.focus();
  }
  document.querySelectorAll('[data-cookie-settings]').forEach((button) => {
    button.hidden = false;
    button.addEventListener('click', () => openPanel(button));
  });
  panel.querySelectorAll('[data-cookie-choice]').forEach((button) => {
    button.addEventListener('click', () => {
      choice = { version, media: button.dataset.cookieChoice === 'media', at: Date.now() };
      try { localStorage.setItem(key, JSON.stringify(choice)); } catch (_) { /* This page only. */ }
      sync();
      closePanel();
    });
  });
  panel.querySelector('[data-cookie-close]').addEventListener('click', closePanel);
  panel.addEventListener('keydown', (event) => { if (event.key === 'Escape' && choice) closePanel(); });
  window.addEventListener('storage', (event) => {
    if (event.key === key || event.key === null) { choice = readChoice(); sync(); panel.hidden = !!choice; }
  });
  window.addEventListener('pageshow', () => { choice = readChoice(); sync(); panel.hidden = !!choice; });
  choice = readChoice();
  sync();
  panel.hidden = !!choice;
})();
