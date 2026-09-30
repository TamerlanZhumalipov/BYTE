// ============================================================
// BYTE — общий JS для сайта
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initNavToggle();
  initFaq();
  initHeroCode();
  initSignupForm();
  initPlanPreselect();
});

/* ---------- Pre-select plan from ?plan=start / ?plan=mentor ---------- */
function initPlanPreselect() {
  const params = new URLSearchParams(window.location.search);
  const plan = params.get('plan');
  if (!plan) return;
  document.querySelectorAll('select[name="plan"]').forEach((select) => {
    select.value = plan;
  });
}

/* ---------- Mobile nav ---------- */
function initNavToggle() {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  if (!toggle || !nav) return;

  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });
}

/* ---------- FAQ accordion ---------- */
function initFaq() {
  const items = document.querySelectorAll('.faq-item');
  items.forEach((item) => {
    const q = item.querySelector('.faq-q');
    const a = item.querySelector('.faq-a');
    if (!q || !a) return;

    q.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');

      items.forEach((other) => {
        other.classList.remove('open');
        const otherA = other.querySelector('.faq-a');
        if (otherA) otherA.style.maxHeight = null;
        const otherQ = other.querySelector('.faq-q');
        if (otherQ) otherQ.setAttribute('aria-expanded', 'false');
      });

      if (!isOpen) {
        item.classList.add('open');
        a.style.maxHeight = a.scrollHeight + 'px';
        q.setAttribute('aria-expanded', 'true');
      }
    });
  });
}

/* ---------- Hero code panel: single typing sequence, then loops ---------- */
function initHeroCode() {
  const body = document.querySelector('[data-code-body]');
  const check = document.querySelector('[data-test-check]');
  if (!body) return;

  const CODE_LINES = [
    { html: '<span class="c-kw">def</span> <span class="c-fn">is_prime</span>(n):' },
    { html: '    <span class="c-kw">if</span> n < 2:' },
    { html: '        <span class="c-kw">return</span> <span class="c-kw">False</span>' },
    { html: '    <span class="c-kw">for</span> i <span class="c-kw">in</span> <span class="c-fn">range</span>(<span class="c-num">2</span>, <span class="c-fn">int</span>(n<span class="c-num">**0.5</span>) + <span class="c-num">1</span>):' },
    { html: '        <span class="c-kw">if</span> n % i == <span class="c-num">0</span>:' },
    { html: '            <span class="c-kw">return</span> <span class="c-kw">False</span>' },
    { html: '    <span class="c-kw">return</span> <span class="c-kw">True</span>' },
    { html: '' },
    { html: '<span class="c-com"># контест: суббота, 18:00</span>' },
    { html: '<span class="c-fn">print</span>(<span class="c-str">"Тестов пройдено: 12/12"</span>)' },
  ];

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    body.innerHTML = renderCodeLines(CODE_LINES);
    if (check) check.classList.add('show');
    return;
  }

  runTypingSequence(body, check, CODE_LINES);
}

function renderCodeLines(lines) {
  return lines
    .map((l) => `<div class="code-line">${l.html || '&nbsp;'}</div>`)
    .join('');
}

function runTypingSequence(container, check, lines) {
  let lineIndex = 0;
  let charIndex = 0;
  container.innerHTML = '';
  if (check) check.classList.remove('show');

  let cursorTarget = document.createElement('div');
  cursorTarget.className = 'code-line';
  container.appendChild(cursorTarget);

  function tick2() {
    if (lineIndex >= lines.length) {
      if (check) check.classList.add('show');
      setTimeout(() => runTypingSequence(container, check, lines), 4200);
      return;
    }
    const fullHtml = lines[lineIndex].html;
    const plainLength = fullHtml.replace(/<[^>]+>/g, '').length;

    if (charIndex <= plainLength) {
      cursorTarget.innerHTML = sliceRichText(fullHtml, charIndex) + '<span class="code-caret"></span>';
      charIndex += 2;
      setTimeout(tick2, 14);
    } else {
      cursorTarget.innerHTML = fullHtml || '&nbsp;';
      lineIndex += 1;
      charIndex = 0;
      const nextLineEl = document.createElement('div');
      nextLineEl.className = 'code-line';
      container.appendChild(nextLineEl);
      cursorTarget = nextLineEl;
      setTimeout(tick2, 60);
    }
  }

  tick2();
}

// Slices visible text length out of a string that contains HTML tags,
// keeping tags intact so colored spans don't break mid-tag.
function sliceRichText(html, visibleLength) {
  let result = '';
  let visibleCount = 0;
  let i = 0;

  while (i < html.length && visibleCount < visibleLength) {
    if (html[i] === '<') {
      const close = html.indexOf('>', i);
      if (close === -1) break;
      result += html.slice(i, close + 1);
      i = close + 1;
    } else {
      result += html[i];
      visibleCount += 1;
      i += 1;
    }
  }

  // close any span left open
  const openSpans = (result.match(/<span/g) || []).length;
  const closedSpans = (result.match(/<\/span>/g) || []).length;
  for (let j = 0; j < openSpans - closedSpans; j += 1) result += '</span>';

  return result;
}

/* ---------- Signup / contact form ---------- */
// This form is designed to be pointed at a Django endpoint.
// Replace the fetch URL below with your real view, e.g. "/api/leads/",
// and add {% csrf_token %} handling once this becomes a Django template.
function initSignupForm() {
  const form = document.querySelector('[data-signup-form]');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const status = form.querySelector('[data-form-status]');
    const button = form.querySelector('button[type="submit"]');
    const originalText = button ? button.textContent : '';

    if (button) {
      button.classList.remove('is-success');
      button.classList.add('is-loading');
      button.disabled = true;
    }

    fetch('/api/leads/', {
      method: 'POST',
      body: new FormData(form), // includes csrfmiddlewaretoken from {% csrf_token %}
    })
      .then((response) => {
        if (!response.ok) throw new Error('request failed');
        return response.json();
      })
      .then(() => {
        if (button) {
          button.classList.remove('is-loading');
          button.classList.add('is-success');
          button.textContent = 'Заявка отправлена ✓';
        }
        if (status) {
          status.textContent = 'Мы свяжемся с вами в течение дня.';
          status.style.color = 'var(--cyan)';
        }
        form.reset();
      })
      .catch(() => {
        if (button) button.classList.remove('is-loading');
        if (status) {
          status.textContent = 'Не получилось отправить заявку. Попробуйте ещё раз.';
          status.style.color = '#e08a8a';
        }
      })
      .finally(() => {
        setTimeout(() => {
          if (button) {
            button.classList.remove('is-loading', 'is-success');
            button.textContent = originalText;
            button.disabled = false;
          }
        }, 2200);
      });
  });
}
