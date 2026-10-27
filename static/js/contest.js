// BYTE — лайв-контест: таймер, задачи, редактор, отправка решений
(function () {
  'use strict';

  const pad = (n) => String(n).padStart(2, '0');
  const formatTime = (s) => `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;

  // ---------- Экран ожидания: обратный отсчёт до начала ----------
  const waitEl = document.getElementById('wait-timer');
  if (waitEl) {
    const startAt = performance.now() + Number(waitEl.dataset.seconds) * 1000;
    const tick = () => {
      const left = Math.max(0, Math.ceil((startAt - performance.now()) / 1000));
      waitEl.textContent = formatTime(left);
      if (left <= 0) {
        window.location.reload();
        return;
      }
      setTimeout(tick, 250);
    };
    tick();
    return;
  }

  const dataEl = document.getElementById('contest-data');
  if (!dataEl) return;

  const data = JSON.parse(dataEl.textContent);
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const $ = (id) => document.getElementById(id);

  const editor = $('cx-editor');
  const langSelect = $('cx-lang');
  const submitBtn = $('cx-submit');
  const runBtn = $('cx-run');
  const isSQL = data.kind === 'sql';
  const kk = document.documentElement.lang === 'kk';
  let busy = false;
  const verdictEl = $('cx-verdict');
  const gridEl = $('cx-grid');
  const messageEl = $('cx-message');
  const historyEl = $('cx-history');
  const noticeEl = $('cx-notice');
  const timerEl = $('cx-timer');
  const barEl = $('cx-bar');
  const closedEl = $('cx-closed');

  const STARTERS = {
    sql: kk ? '-- Ашық кестелер бойынша SELECT сұрауын жазыңыз\n' : '-- Напишите SELECT-запрос к открытым таблицам\n',
    python: '# Читайте данные через input(), ответ выводите через print()\n',
    cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    // ваш код\n    return 0;\n}\n',
  };
  const VERDICT_TEXT = {
    OK: 'Принято — все тесты пройдены',
    WA: 'Неверный ответ',
    TLE: 'Превышено время',
    RE: 'Ошибка выполнения',
    CE: 'Ошибка компиляции',
  };
  const SQL_VERDICT_TEXT = {
    OK: kk ? 'Шешім дұрыс' : 'Решение верное',
    WA: kk ? 'Нәтиже қате' : 'Неверный результат',
    TLE: kk ? 'Уақыт шегінен асты' : 'Превышено время',
    RE: kk ? 'Сұрауды орындау қатесі' : 'Ошибка выполнения запроса',
    CE: kk ? 'Сұрау қатесі' : 'Ошибка запроса',
  };
  const CELL_CLASS = { P: 'p', F: 'f', T: 't', E: 'e' };
  const CELL_GLYPH = { P: '✓', F: '✕', T: 'T', E: '!' };
  const CELL_TITLE = { P: 'верно', F: 'неверный ответ', T: 'превышено время', E: 'ошибка выполнения' };

  const tasks = new Map(data.tasks.map((t) => [t.id, t]));
  let currentId = data.tasks.length ? data.tasks[0].id : null;
  let activeLang = isSQL ? 'sql' : 'python';
  let locked = data.state !== 'running';
  let endAt = performance.now() + data.remaining * 1000;
  let trapTab = true;

  // ---------- Черновики (сохраняются в браузере, переживают перезагрузку) ----------
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* хранилище недоступно */ } },
  };
  const prefix = `byte:${data.contestId}:${data.accountId}`;
  const codeKey = (taskId, lang) => `${prefix}:code:${taskId}:${lang}`;
  const langKey = (taskId) => `${prefix}:lang:${taskId}`;

  function saveDraft() {
    if (currentId !== null) store.set(codeKey(currentId, activeLang), editor.value);
  }

  function loadEditor() {
    activeLang = isSQL ? 'sql' : (store.get(langKey(currentId)) === 'cpp' ? 'cpp' : 'python');
    langSelect.value = activeLang;
    const saved = store.get(codeKey(currentId, activeLang));
    editor.value = saved !== null ? saved : STARTERS[activeLang];
  }

  // ---------- Результаты ----------
  function renderGrid(marks, total) {
    if (!gridEl || isSQL) return;
    gridEl.innerHTML = '';
    for (let i = 0; i < total; i += 1) {
      const mark = marks[i] || '-';
      const cell = document.createElement('span');
      cell.className = `cx-cell ${CELL_CLASS[mark] || ''}`;
      cell.textContent = CELL_GLYPH[mark] || '';
      cell.title = `Тест ${i + 1}: ${CELL_TITLE[mark] || 'не проверялся'}`;
      gridEl.appendChild(cell);
    }
  }

  function setMessage(text) {
    messageEl.textContent = text || '';
    messageEl.hidden = !text;
  }

  function setNotice(text) {
    noticeEl.textContent = text || '';
    noticeEl.hidden = !text;
  }

  function showSubmission(sub, task) {
    verdictEl.className = `cx-verdict ${sub.verdict.toLowerCase()}`;
    verdictEl.textContent = isSQL ? (SQL_VERDICT_TEXT[sub.verdict] || sub.label) : `${VERDICT_TEXT[sub.verdict] || sub.label} · ${sub.passed}/${sub.total || task.total} тестов`;
    renderGrid(sub.marks || '', sub.total || task.total);
    setMessage(sub.message);
  }

  function renderHistory(task) {
    historyEl.innerHTML = '';
    if (!task.history.length) {
      const li = document.createElement('li');
      li.textContent = 'Отправок пока нет';
      historyEl.appendChild(li);
      return;
    }
    task.history.forEach((sub) => {
      const li = document.createElement('li');
      li.innerHTML = '<span class="v"></span><span class="score"></span><span class="lang"></span><span class="when"></span>';
      const v = li.querySelector('.v');
      v.textContent = isSQL ? (SQL_VERDICT_TEXT[sub.verdict] || sub.label) : (VERDICT_TEXT[sub.verdict] ? sub.label : sub.verdict);
      v.classList.add(sub.verdict.toLowerCase());
      li.querySelector('.score').textContent = isSQL ? '' : `${sub.passed}/${sub.total}`;
      li.querySelector('.lang').textContent = sub.language === 'sql' ? 'SQL' : (sub.language === 'cpp' ? 'C++' : 'Python');
      li.querySelector('.when').textContent = sub.time;
      historyEl.appendChild(li);
    });
  }

  function updateChip(task) {
    const chip = document.querySelector(`[data-chip="${task.id}"]`);
    if (!chip) return;
    chip.textContent = isSQL ? (task.best ? (kk ? "Шешілді" : "Решена") : (kk ? "Шешілмеді" : "Не решена")) : `${task.best}/${task.total}`;
    chip.classList.toggle('is-full', task.total > 0 && task.best === task.total);
  }

  function renderTaskResult() {
    const task = tasks.get(currentId);
    if (!task) return;
    setNotice('');
    if (task.history.length) {
      showSubmission(task.history[0], task);
    } else {
      verdictEl.className = 'cx-verdict';
      verdictEl.textContent = 'Отправьте решение — здесь появится результат проверки.';
      renderGrid('', task.total);
      setMessage('');
    }
    renderHistory(task);
  }

  // ---------- Вкладки задач ----------
  function showTask(id) {
    currentId = id;
    document.querySelectorAll('[data-task-tab]').forEach((btn) => {
      const on = Number(btn.dataset.taskTab) === id;
      btn.classList.toggle('is-active', on);
      btn.setAttribute('aria-selected', String(on));
    });
    document.querySelectorAll('[data-task-panel]').forEach((panel) => {
      panel.hidden = Number(panel.dataset.taskPanel) !== id;
    });
    loadEditor();
    renderTaskResult();
    if (isSQL) { $('cx-run-table').replaceChildren(); $('cx-run-status').textContent = kk ? 'Сұрауды ашық деректерде іске қосыңыз.' : 'Запустите запрос на открытых данных.'; }
  }

  document.querySelectorAll('[data-task-tab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = Number(btn.dataset.taskTab);
      if (id === currentId) return;
      saveDraft();
      showTask(id);
    });
  });

  // ---------- Редактор ----------
  langSelect.addEventListener('change', () => {
    saveDraft(); // сохраняем код на прежнем языке
    activeLang = langSelect.value;
    store.set(langKey(currentId), activeLang);
    const saved = store.get(codeKey(currentId, activeLang));
    editor.value = saved !== null ? saved : STARTERS[activeLang];
  });

  editor.addEventListener('input', saveDraft);

  editor.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
      return;
    }
    if (e.key === 'Escape') { trapTab = false; return; }   // Esc, затем Tab — выйти из редактора
    if (e.key === 'Tab' && trapTab && !e.shiftKey) {
      e.preventDefault();
      editor.setRangeText('    ', editor.selectionStart, editor.selectionEnd, 'end');
      saveDraft();
      return;
    }
    if (e.key !== 'Tab' && e.key !== 'Shift') trapTab = true;
  });

  // ---------- Блокировка после конца контеста ----------
  function lockUI(message) {
    locked = true;
    editor.readOnly = true;
    langSelect.disabled = true;
    submitBtn.disabled = true;
    if (runBtn) runBtn.disabled = true;
    if (message) {
      closedEl.textContent = message;
      closedEl.hidden = false;
    }
  }

  // ---------- Отправка решения ----------
  async function submit() {
    if (locked || busy || submitBtn.disabled || currentId === null) return;
    const code = editor.value;
    if (!code.trim()) {
      setNotice('Напишите решение перед отправкой.');
      return;
    }
    saveDraft();
    setNotice('');
    busy = true;
    submitBtn.disabled = true;
    if (runBtn) runBtn.disabled = true;
    submitBtn.classList.add('is-loading');
    verdictEl.className = 'cx-verdict';
    verdictEl.textContent = isSQL ? (kk ? 'Шешім тексерілуде…' : 'Проверяем решение…') : 'Проверяем на тестах…';

    const taskId = currentId;
    try {
      const response = await fetch(data.submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ task_id: taskId, language: activeLang, code }),
      });
      const body = await response.json().catch(() => ({}));

      if (!response.ok) {
        if (body.state === 'finished') lockUI('Контест завершён. Отправка решений закрыта.');
        renderTaskResult(); // возвращаем прежний результат вместо «Проверяем…»
        setNotice(body.error || 'Не удалось отправить решение. Попробуйте ещё раз.');
        return;
      }

      const task = tasks.get(taskId);
      task.history.unshift(body.submission);
      task.history = task.history.slice(0, 8);
      task.best = body.best;
      if (typeof body.remaining === 'number') endAt = performance.now() + body.remaining * 1000;
      updateChip(task);
      if (taskId === currentId) {
        showSubmission(body.submission, task);
        renderHistory(task);
      }
    } catch (err) {
      renderTaskResult();
      setNotice('Нет связи с сервером. Проверьте интернет и отправьте ещё раз.');
    } finally {
      busy = false;
      submitBtn.classList.remove('is-loading');
      if (!locked) { submitBtn.disabled = false; if (runBtn) runBtn.disabled = false; }
    }
  }

  async function runSQL() {
    if (locked || busy || currentId === null) return;
    if (!editor.value.trim()) { setNotice(kk ? 'SQL сұрауын жазыңыз.' : 'Напишите SQL-запрос.'); return; }
    const taskId = currentId;
    busy = true;
    runBtn.disabled = true;
    submitBtn.disabled = true;
    saveDraft();
    setNotice('');
    $('cx-run-table').replaceChildren();
    $('cx-run-status').textContent = kk ? 'Орындалуда…' : 'Выполняем…';
    try {
      const response = await fetch(data.runUrl, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ task_id: taskId, code: editor.value }),
      });
      const body = await response.json();
      if (body.state === 'finished') lockUI(kk ? 'Контест аяқталды.' : 'Контест завершён.');
      if (currentId !== taskId) return; // Ignore an older task's response after switching tabs.
      if (!response.ok || body.status !== 'OK') {
        $('cx-run-status').textContent = body.error || body.message || (kk ? 'Сұрау орындалмады.' : 'Запрос не выполнен.');
        return;
      }
      $('cx-run-status').textContent = `${body.rows.length} ${kk ? 'жол · ұпайға әсер етпейді' : 'строк · не влияет на баллы'}`;
      const table = document.createElement('table');
      const head = table.createTHead().insertRow();
      body.columns.forEach((column) => { const th = document.createElement('th'); th.textContent = column; head.append(th); });
      const tbody = table.createTBody();
      body.rows.forEach((row) => { const tr = tbody.insertRow(); row.forEach((value) => { const td = tr.insertCell(); td.textContent = value === null ? 'NULL' : String(value); if (value === null) td.className = 'cx-null'; }); });
      $('cx-run-table').append(table);
    } catch (_) {
      if (currentId === taskId) $('cx-run-status').textContent = kk ? 'Сервермен байланыс жоқ.' : 'Нет связи с сервером.';
    } finally {
      busy = false;
      if (!locked) { runBtn.disabled = false; submitBtn.disabled = false; }
    }
  }
  if (runBtn) runBtn.addEventListener('click', runSQL);
  submitBtn.addEventListener('click', submit);

  // ---------- Таймер ----------
  function tickTimer() {
    const left = Math.max(0, Math.ceil((endAt - performance.now()) / 1000));
    timerEl.textContent = formatTime(left);
    timerEl.classList.toggle('is-warn', left > 0 && left <= 300);
    timerEl.classList.toggle('is-over', left === 0);
    const elapsedShare = data.state === 'running' ? 1 - left / data.duration : 1;
    barEl.style.width = `${Math.min(100, Math.max(0, elapsedShare * 100))}%`;
    if (left === 0 && !locked) lockUI('Время вышло. Отправка решений закрыта — ваши результаты сохранены.');
  }

  // ---------- Старт ----------
  data.tasks.forEach(updateChip);
  if (currentId !== null) showTask(currentId);
  if (locked || currentId === null) lockUI('');
  tickTimer();
  setInterval(tickTimer, 250);
})();
