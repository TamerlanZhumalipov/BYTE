// BYTE AI — floating assistant with session-only history
(() => {
  'use strict';

  function initByteAI() {
    const root = document.getElementById('ai');
    if (!root || root.dataset.ready === '1') return;
    root.dataset.ready = '1';

    if (root.parentElement !== document.body) document.body.appendChild(root);

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrf = csrfMeta ? csrfMeta.content : '';
    const askUrl = root.dataset.askUrl;
    const resetUrl = root.dataset.resetUrl;
    const storageKey = `byte-ai-session:${askUrl}`;

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

    const greeting =
      messagesEl.querySelector('.ai-msg-assistant .ai-bubble')?.textContent?.trim() ||
      'Сәлем! Я BYTE AI. Чем могу помочь?';

    function loadHistory() {
      try {
        const parsed = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
        if (!Array.isArray(parsed)) return [];
        return parsed
          .filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
          .slice(-16);
      } catch {
        return [];
      }
    }

    let sessionHistory = loadHistory();

    function saveHistory() {
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(sessionHistory.slice(-16)));
      } catch {
        // Chat still works if sessionStorage is unavailable.
      }
    }

    function openPanel() {
      root.classList.add('is-open');
      panel.setAttribute('aria-hidden', 'false');
      fab.setAttribute('aria-expanded', 'true');
      fab.classList.add('is-open');
      messagesEl.scrollTop = messagesEl.scrollHeight;
      requestAnimationFrame(() => input.focus());
    }

    function closePanel() {
      root.classList.remove('is-open');
      panel.setAttribute('aria-hidden', 'true');
      fab.setAttribute('aria-expanded', 'false');
      fab.classList.remove('is-open');
    }

    closePanel();

    fab.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      root.classList.contains('is-open') ? closePanel() : openPanel();
    });

    closeBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      closePanel();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && root.classList.contains('is-open')) closePanel();
    });

    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 140) + 'px';
    });

    function createBubble(role) {
      const wrap = document.createElement('div');
      wrap.className = `ai-msg ai-msg-${role}`;
      const bubble = document.createElement('div');
      bubble.className = 'ai-bubble';
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return bubble;
    }

    function addMessage(role, text) {
      const bubble = createBubble(role);
      bubble.textContent = text;
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return bubble;
    }

    function typeAssistantMessage(text) {
      const bubble = createBubble('assistant');
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      if (reduceMotion || !text) {
        bubble.textContent = text;
        return Promise.resolve();
      }

      return new Promise((resolve) => {
        const speed = 95; // characters per second
        const started = performance.now();
        let shown = 0;

        function frame(now) {
          const target = Math.min(text.length, Math.floor(((now - started) / 1000) * speed));
          if (target > shown) {
            bubble.textContent = text.slice(0, target);
            shown = target;
            messagesEl.scrollTop = messagesEl.scrollHeight;
          }

          if (shown < text.length) {
            requestAnimationFrame(frame);
          } else {
            bubble.textContent = text;
            messagesEl.scrollTop = messagesEl.scrollHeight;
            resolve();
          }
        }

        requestAnimationFrame(frame);
      });
    }

    function renderSessionHistory() {
      if (!sessionHistory.length) return;
      messagesEl.innerHTML = '';
      sessionHistory.forEach((message) => addMessage(message.role, message.content));
    }

    renderSessionHistory();

    function addTyping() {
      root.querySelector('#ai-typing')?.remove();
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

      const priorHistory = sessionHistory.slice(-8);

      addMessage('user', text);
      sessionHistory.push({ role: 'user', content: text });
      saveHistory();

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
          body: JSON.stringify({
            message: text,
            history: priorHistory,
          }),
        });

        const body = await response.json().catch(() => ({}));
        removeTyping();

        if (!response.ok) {
          addMessage('assistant', body.error || 'Не получилось получить ответ. Попробуйте ещё раз.');
          return;
        }

        const answer = body.content || 'Ответ пуст. Попробуйте переформулировать вопрос.';
        await typeAssistantMessage(answer);
        sessionHistory.push({ role: 'assistant', content: answer });
        saveHistory();
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

      sessionHistory = [];
      try {
        sessionStorage.removeItem(storageKey);
      } catch {}

      messagesEl.innerHTML = '';
      addMessage('assistant', greeting);

      // Server-side log reset is best-effort; UI/session reset does not depend on it.
      try {
        await fetch(resetUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
        });
      } catch {}

      input.focus();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initByteAI, { once: true });
  } else {
    initByteAI();
  }
})();
