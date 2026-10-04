// No HTML from the model is injected. Fenced code is rendered with textContent.
document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('byteAiButton');
  if (!button) return;
  const panel = document.getElementById('byteAiWindow');
  const messages = document.getElementById('byteAiMessages');
  const input = document.getElementById('byteAiInput');
  const send = document.getElementById('byteAiSend');
  const clear = document.getElementById('byteAiClear');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const suggestions = document.querySelector('.ai-suggestions');
  let busy = false;
  let loaded = false;
  const scroll = () => { messages.scrollTop = messages.scrollHeight; };
  function setBusy(value) {
    busy = value;
    send.disabled = value;
    clear.disabled = value;
    input.disabled = value;
    suggestions.querySelectorAll('button').forEach(item => { item.disabled = value; });
    messages.setAttribute('aria-busy', String(value));
  }
  function message(text, role = 'bot') {
    const el = document.createElement('div');
    el.className = `byte-ai-message byte-ai-message-${role}`;
    el.textContent = text;
    messages.append(el);
    scroll();
    return el;
  }
  function renderAnswer(el, text) {
    el.replaceChildren();
    const chunks = text.split(/```/);
    chunks.forEach((chunk, index) => {
      if (index % 2 === 0) { el.append(document.createTextNode(chunk)); return; }
      const newline = chunk.indexOf('\n');
      const language = newline >= 0 ? chunk.slice(0, newline).trim() : '';
      const source = newline >= 0 ? chunk.slice(newline + 1).replace(/\n$/, '') : chunk;
      const wrap = document.createElement('div');
      wrap.className = 'ai-code';
      const bar = document.createElement('div');
      bar.className = 'ai-code-bar';
      const label = document.createElement('span');
      label.textContent = language || 'Код';
      const copy = document.createElement('button');
      copy.type = 'button'; copy.textContent = 'Копировать';
      copy.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(source); copy.textContent = 'Скопировано'; }
        catch (_) { copy.textContent = 'Выдели код вручную'; }
      });
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = source; pre.append(code); bar.append(label, copy); wrap.append(bar, pre); el.append(wrap);
    });
    scroll();
  }
  async function api(data) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 40000);
    try {
      const response = await fetch('/api/ai/', {
        method: data ? 'POST' : 'GET', signal: controller.signal,
        headers: data ? { 'Content-Type': 'application/json', 'X-CSRFToken': csrf } : {},
        ...(data ? {body: JSON.stringify(data)} : {})
      });
      if (response.status === 403) throw new Error('Обнови страницу и повтори запрос.');
      if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Сессия завершилась. Войди в кабинет заново.');
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Не удалось получить ответ.');
      return result;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Ответ занимает слишком много времени. Попробуй ещё раз.');
      if (error instanceof TypeError) throw new Error('Нет соединения с сервером. Проверь интернет и повтори вопрос.');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  function open() {
    panel.hidden = false;
    panel.classList.add('is-open');
    button.setAttribute('aria-expanded', 'true');
    input.focus();
    if (!loaded && !busy) restore();
  }
  function close() {
    panel.hidden = true; panel.classList.remove('is-open');
    button.setAttribute('aria-expanded', 'false'); button.focus();
  }
  async function restore() {
    setBusy(true);
    try {
      const result = await api();
      if (result.history.length) {
        messages.replaceChildren();
        result.history.forEach(item => { const el = message('', item.role === 'user' ? 'user' : 'bot'); renderAnswer(el, item.text); });
      }
      if (!result.configured) message('AI-помощник ещё не подключён. Преподаватель сможет активировать его в настройках сайта.');
      loaded = true;
    } catch (error) { message(error.message); }
    finally { setBusy(false); if (!panel.hidden) input.focus(); }
  }
  async function sendMessage(retryText, retryElement) {
    if (busy) return;
    const text = typeof retryText === 'string' ? retryText : input.value.trim();
    if (!text || text.length > 4000) return;
    retryElement?.remove();
    if (!retryText) message(text, 'user');
    input.value = ''; input.style.height = '';
    setBusy(true);
    const pending = message('Разбираюсь в вопросе…');
    pending.classList.add('ai-pending');
    try {
      const result = await api({ question: text, section: document.body.dataset.section || '' });
      pending.classList.remove('ai-pending');
      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const parts = result.answer.match(/\S+\s*/g) || [result.answer];
        const step = Math.max(1, Math.ceil(parts.length / 35));
        pending.textContent = '';
        for (let i = 0; i < parts.length; i += step) {
          pending.append(document.createTextNode(parts.slice(i, i + step).join('')));
          scroll();
          await new Promise(resolve => setTimeout(resolve, 25));
        }
      }
      renderAnswer(pending, result.answer);
    } catch (error) {
      pending.classList.remove('ai-pending');
      pending.textContent = error.message;
      pending.classList.add('ai-error');
      const retry = document.createElement('button'); retry.className = 'ai-retry'; retry.type = 'button'; retry.textContent = 'Повторить вопрос';
      retry.addEventListener('click', () => sendMessage(text, pending));
      pending.append(retry);
    } finally { setBusy(false); if (!panel.hidden) input.focus(); scroll(); }
  }
  button.addEventListener('click', () => panel.hidden ? open() : close());
  document.getElementById('byteAiClose').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) close(); });
  send.addEventListener('click', () => sendMessage());
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage(); } });
  input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 120)}px`; });
  document.querySelectorAll('[data-ai-prompt]').forEach(el => el.addEventListener('click', () => { input.value = el.dataset.aiPrompt; input.focus(); }));
  clear.addEventListener('click', async () => {
    if (busy) return;
    setBusy(true);
    try { await api({action: 'clear'}); messages.replaceChildren(); message('Начнём заново. Какую тему разберём?'); }
    catch (error) { message(error.message); }
    finally { setBusy(false); input.focus(); }
  });
});
