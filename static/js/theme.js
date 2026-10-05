(() => {
  const key = 'byte-theme';
  const root = document.documentElement;
  const saved = localStorage.getItem(key);
  if (saved === 'light') root.classList.add('light-theme');

  function syncButton() {
    const button = document.getElementById('themeButton');
    if (!button) return;
    const light = root.classList.contains('light-theme');
    button.textContent = light ? '☾' : '☀';
    button.setAttribute('aria-label', light ? 'Включить тёмную тему' : 'Включить светлую тему');
    button.title = light ? 'Тёмная тема' : 'Светлая тема';
  }

  document.addEventListener('DOMContentLoaded', () => {
    syncButton();
    document.getElementById('themeButton')?.addEventListener('click', () => {
      root.classList.toggle('light-theme');
      localStorage.setItem(key, root.classList.contains('light-theme') ? 'light' : 'dark');
      syncButton();
    });
  });
})();
