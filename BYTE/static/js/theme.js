// Run in <head> before styles paint; respect the OS until a preference is saved.
(() => {
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference;
  try { preference = localStorage.getItem('byte-theme'); } catch (_) { /* Private mode. */ }
  if (!['light', 'dark'].includes(preference)) preference = null;
  const apply = theme => {
    root.classList.toggle('light-theme', theme === 'light');
    root.classList.toggle('dark-theme', theme === 'dark');
    root.style.colorScheme = theme;
    const button = document.getElementById('themeButton');
    if (button) {
      button.textContent = theme === 'light' ? '☾' : '☀';
      button.setAttribute('aria-label', theme === 'light' ? 'Включить тёмную тему' : 'Включить светлую тему');
      button.title = button.getAttribute('aria-label');
    }
  };
  const current = () => preference || (system.matches ? 'dark' : 'light');
  apply(current());
  document.addEventListener('DOMContentLoaded', () => {
    apply(current());
    document.getElementById('themeButton')?.addEventListener('click', () => {
      preference = root.classList.contains('light-theme') ? 'dark' : 'light';
      try { localStorage.setItem('byte-theme', preference); } catch (_) { /* Keep in memory. */ }
      apply(preference);
    });
  });
  system.addEventListener('change', () => { if (!preference) apply(current()); });
  window.addEventListener('storage', event => { if (event.key === 'byte-theme') { preference = ['light', 'dark'].includes(event.newValue) ? event.newValue : null; apply(current()); } });
})();
