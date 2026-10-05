// BYTE AI 2.0 — safe rendering, lesson context, robust launcher and retry UX.
document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('byteAiButton');
  const panel = document.getElementById('byteAiWindow');
  if (!button || !panel) return;
  const messages = document.getElementById('byteAiMessages');
  const input = document.getElementById('byteAiInput');
  const send = document.getElementById('byteAiSend');
  const clear = document.getElementById('byteAiClear');
  const closeButton = document.getElementById('byteAiClose');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const suggestions = document.querySelector('.ai-suggestions');
  let busy = false, loaded = false;
  const scroll = () => { messages.scrollTop = messages.scrollHeight; };

  function setBusy(value) {
    busy = value; send.disabled = value; clear.disabled = value; input.disabled = value;
    suggestions?.querySelectorAll('button').forEach(item => { item.disabled = value; });
    messages.setAttribute('aria-busy', String(value));
  }
  function message(text, role = 'bot') {
    const el = document.createElement('div');
    el.className = `byte-ai-message byte-ai-message-${role}`;
    if (role === 'bot') { const label = document.createElement('span'); label.className = 'ai-message-label'; label.textContent = 'BYTE AI'; el.append(label); }
    el.append(document.createTextNode(text)); messages.append(el); scroll(); return el;
  }
  function renderAnswer(el, text) {
    el.replaceChildren();
    const label = document.createElement('span'); label.className = 'ai-message-label'; label.textContent = 'BYTE AI'; el.append(label);
    const chunks = text.split(/```/);
    chunks.forEach((chunk, index) => {
      if (index % 2 === 0) { el.append(document.createTextNode(chunk)); return; }
      const newline = chunk.indexOf('\n'); const language = newline >= 0 ? chunk.slice(0,newline).trim() : '';
      const source = newline >= 0 ? chunk.slice(newline+1).replace(/\n$/,'') : chunk;
      const wrap = document.createElement('div'); wrap.className='ai-code';
      const bar=document.createElement('div'); bar.className='ai-code-bar'; const lang=document.createElement('span'); lang.textContent=language||'Код';
      const copy=document.createElement('button'); copy.type='button'; copy.textContent='Копировать'; copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(source);copy.textContent='Скопировано ✓'}catch(_){copy.textContent='Выдели вручную'}});
      const pre=document.createElement('pre'), code=document.createElement('code'); code.textContent=source; pre.append(code); bar.append(lang,copy); wrap.append(bar,pre); el.append(wrap);
    }); scroll();
  }
  async function api(data) {
    const controller=new AbortController(); const timeout=setTimeout(()=>controller.abort(),45000);
    try {
      const response=await fetch('/api/ai/',{method:data?'POST':'GET',signal:controller.signal,headers:data?{'Content-Type':'application/json','X-CSRFToken':csrf}:{},...(data?{body:JSON.stringify(data)}:{})});
      if(response.status===401) throw new Error('Сессия завершилась. Войди в кабинет заново.');
      if(response.status===403) throw new Error('Обнови страницу и повтори запрос.');
      if(!response.headers.get('content-type')?.includes('application/json')) throw new Error('Сервер вернул неожиданный ответ. Обнови страницу.');
      const result=await response.json(); if(!response.ok||!result.ok) throw new Error(result.error||'Не удалось получить ответ.'); return result;
    } catch(error) {
      if(error.name==='AbortError') throw new Error('BYTE AI отвечает дольше обычного. Попробуй ещё раз.');
      if(error instanceof TypeError) throw new Error('Нет соединения с сервером. Проверь интернет.'); throw error;
    } finally { clearTimeout(timeout); }
  }
  function open(){panel.hidden=false;panel.classList.add('is-open');button.setAttribute('aria-expanded','true');if(!loaded&&!busy)restore();else input.focus()}
  function close(){panel.hidden=true;panel.classList.remove('is-open');button.setAttribute('aria-expanded','false')}
  async function restore(){setBusy(true);try{const result=await api();if(result.history?.length){messages.replaceChildren();result.history.forEach(item=>{const el=message('',item.role==='user'?'user':'bot');if(item.role==='user')el.textContent=item.text;else renderAnswer(el,item.text)})}if(!result.configured)message('AI ещё не подключён к серверу. Проверь GEMINI_API_KEY в настройках проекта.');loaded=true}catch(error){message(error.message)}finally{setBusy(false);if(!panel.hidden)input.focus()}}
  async function sendMessage(retryText,retryElement){if(busy)return;const text=typeof retryText==='string'?retryText:input.value.trim();if(!text||text.length>4000)return;retryElement?.remove();if(!retryText)message(text,'user');input.value='';input.style.height='';setBusy(true);const pending=message('Думаю над ответом…');pending.classList.add('ai-pending');try{const result=await api({question:text,section:document.body.dataset.section||''});pending.classList.remove('ai-pending');renderAnswer(pending,result.answer)}catch(error){pending.classList.remove('ai-pending');pending.classList.add('ai-error');pending.replaceChildren();const label=document.createElement('span');label.className='ai-message-label';label.textContent='BYTE AI';pending.append(label,document.createTextNode(error.message));const retry=document.createElement('button');retry.className='ai-retry';retry.type='button';retry.textContent='Попробовать снова';retry.addEventListener('click',()=>sendMessage(text,pending));pending.append(retry)}finally{setBusy(false);if(!panel.hidden)input.focus();scroll()}}
  button.addEventListener('click',()=>panel.hidden?open():close()); closeButton?.addEventListener('click',close);
  document.querySelectorAll('[data-open-byte-ai]').forEach(el=>el.addEventListener('click',open));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)close()}); send.addEventListener('click',()=>sendMessage());
  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage()}}); input.addEventListener('input',()=>{input.style.height='auto';input.style.height=`${Math.min(input.scrollHeight,120)}px`});
  document.querySelectorAll('[data-ai-prompt]').forEach(el=>el.addEventListener('click',()=>{open();input.value=el.dataset.aiPrompt;input.focus()}));
  clear.addEventListener('click',async()=>{if(busy)return;setBusy(true);try{await api({action:'clear'});messages.replaceChildren();message('Новый чат открыт. Что разберём?')}catch(error){message(error.message)}finally{setBusy(false);input.focus()}});
});
