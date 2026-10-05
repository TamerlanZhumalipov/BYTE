// BYTE — ИИ-помощник по материалам: чат-панель на странице раздела
(function () {
  'use strict';

  const root = document.getElementById('ai');
  if (!root) return;

  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const askUrl = root.dataset.askUrl;
  const resetUrl = root.dataset.resetUrl;

  const fab = document.getElementById('ai-fab');
  const panel = document.getElementById('ai-panel');
  const closeBtn = document.getElementById('ai-close');
  const resetBtn = document.getElementById('ai-reset');
  const messagesEl = document.getElementById('ai-messages');
  const form = document.getElementById('ai-form');
  const input = document.getElementById('ai-input');
  const submitBtn = form.querySelector('button[type="submit"]');

  function openPanel() {
    panel.hidden = false;
    fab.setAttribute('aria-expanded', 'true');
    fab.classList.add('is-open');
    messagesEl.scrollTop = messagesEl.scrollHeight;
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
    fab.classList.remove('is-open');
  }

  fab.addEventListener('click', () => (panel.hidden ? openPanel() : closePanel()));
  closeBtn.addEventListener('click', closePanel);

  // Textarea растёт вместе с текстом, но не бесконечно
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
    const wrap = document.createElement('div');
    wrap.className = 'ai-msg ai-msg-assistant';
    wrap.id = 'ai-typing';
    wrap.innerHTML = '<div class="ai-bubble ai-typing"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById('ai-typing');
    if (el) el.remove();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
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
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ message: text }),
      });
      const body = await response.json().catch(() => ({}));
      removeTyping();

      if (!response.ok) {
        addMessage('assistant', body.error || 'Не получилось получить ответ. Попробуйте ещё раз.');
        return;
      }
      addMessage('assistant', body.content);
    } catch (err) {
      removeTyping();
      addMessage('assistant', 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.');
    } finally {
      submitBtn.disabled = false;
    }
  });

  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  resetBtn.addEventListener('click', async () => {
    if (!window.confirm('Начать новый диалог? Текущая переписка скроется (куратор всё ещё сможет её увидеть).')) return;
    resetBtn.disabled = true;
    try {
      await fetch(resetUrl, { method: 'POST', headers: { 'X-CSRFToken': csrf } });
    } catch (err) {
      // даже если запрос не дошёл, очищаем окно — на сервере ничего страшного не произойдёт
    }
    messagesEl.innerHTML = '';
    addMessage('assistant', 'Начали новый диалог. Спрашивайте!');
    resetBtn.disabled = false;
  });
})();
