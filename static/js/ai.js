// BYTE AI — floating assistant
(() => {
  'use strict';

  function initByteAI() {
    const root = document.getElementById('ai');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';

    // Move the assistant to <body> so no dashboard/grid/animation container
    // can change the containing block of position: fixed.
    if (root.parentElement !== document.body) document.body.appendChild(root);

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrf = csrfMeta ? csrfMeta.content : '';
    const askUrl = root.dataset.askUrl;
    const resetUrl = root.dataset.resetUrl;

    const fab = root.querySelector('#ai-fab');
    const panel = root.querySelector('#ai-panel');
    const closeBtn = root.querySelector('#ai-close');
    const resetBtn = root.querySelector('#ai-reset');
    const messagesEl = root.querySelector('#ai-messages');
    const form = root.querySelector('#ai-form');
    const input = root.querySelector('#ai-input');
    const submitBtn = form?.querySelector('button[type="submit"]');

    if (!fab || !panel || !messagesEl || !form || !input || !submitBtn) {
      console.error('BYTE AI: interface elements are missing');
      return;
    }

    function openPanel() {
      panel.hidden = false;
      panel.setAttribute('aria-hidden', 'false');
      fab.setAttribute('aria-expanded', 'true');
      fab.classList.add('is-open');
      messagesEl.scrollTop = messagesEl.scrollHeight;
      requestAnimationFrame(() => input.focus());
    }

    function closePanel() {
      panel.hidden = true;
      panel.setAttribute('aria-hidden', 'true');
      fab.setAttribute('aria-expanded', 'false');
      fab.classList.remove('is-open');
    }

    closePanel();

    fab.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      panel.hidden ? openPanel() : closePanel();
    });

    closeBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      closePanel();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !panel.hidden) closePanel();
    });

    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 140) + 'px';
    });

    function addMessage(role, text) {
      const wrap = document.createElement('div');
      wrap.className = `ai-msg ai-msg-${role}`;
      const bubble = document.createElement('div');
      bubble.className = 'ai-bubble';
      bubble.textContent = text;
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return bubble;
    }

    function addTyping() {
      const existing = root.querySelector('#ai-typing');
      if (existing) existing.remove();
      const wrap = document.createElement('div');
      wrap.className = 'ai-msg ai-msg-assistant';
      wrap.id = 'ai-typing';
      wrap.innerHTML = '<div class="ai-bubble ai-typing"><span></span><span></span><span></span></div>';
      messagesEl.appendChild(wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function removeTyping() {
      root.querySelector('#ai-typing')?.remove();
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text || submitBtn.disabled) return;

      addMessage('user', text);
      input.value = '';
      input.style.height = 'auto';
      submitBtn.disabled = true;
      addTyping();

      try {
        const response = await fetch(askUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: JSON.stringify({ message: text }),
        });
        const body = await response.json().catch(() => ({}));
        removeTyping();

        if (!response.ok) {
          addMessage('assistant', body.error || 'Не получилось получить ответ. Попробуйте ещё раз.');
          return;
        }
        addMessage('assistant', body.content || 'Ответ пуст. Попробуйте переформулировать вопрос.');
      } catch (error) {
        removeTyping();
        addMessage('assistant', 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.');
      } finally {
        submitBtn.disabled = false;
        input.focus();
      }
    });

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    resetBtn?.addEventListener('click', async () => {
      if (!window.confirm('Начать новый диалог?')) return;
      resetBtn.disabled = true;
      try {
        const response = await fetch(resetUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) throw new Error('reset failed');
        messagesEl.innerHTML = '';
        addMessage('assistant', 'Начали новый диалог. Спрашивайте!');
      } catch (error) {
        addMessage('assistant', 'Не удалось начать новый диалог. Попробуйте ещё раз.');
      } finally {
        resetBtn.disabled = false;
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initByteAI, { once: true });
  } else {
    initByteAI();
  }
})();
