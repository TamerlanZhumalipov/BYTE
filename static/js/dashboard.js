// BYTE — кабинет: боковое меню материалов на телефоне
document.addEventListener('DOMContentLoaded', () => {
  const side = document.getElementById('dash-side');
  const toggle = document.querySelector('[data-side-toggle]');
  if (!side) return;

  if (toggle) {
    toggle.addEventListener('click', () => {
      const open = side.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });

    document.addEventListener('click', (e) => {
      if (side.classList.contains('is-open') && !side.contains(e.target) && !toggle.contains(e.target)) {
        side.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Показываем текущий раздел в меню, не сдвигая саму страницу
  const current = side.querySelector('.is-current');
  if (current) current.scrollIntoView({ block: 'nearest' });
});
