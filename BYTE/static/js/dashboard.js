document.addEventListener('DOMContentLoaded', () => {
  const side = document.getElementById('dash-side');
  const toggle = document.querySelector('[data-side-toggle]');
  if (!side || !toggle) return;
  const mobile = window.matchMedia('(max-width: 900px)');
  const setOpen = open => {
    side.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    side.inert = mobile.matches && !open;
  };
  setOpen(false);
  mobile.addEventListener('change', () => setOpen(false));
  toggle.addEventListener('click', () => setOpen(!side.classList.contains('is-open')));
  document.addEventListener('click', event => {
    if (side.classList.contains('is-open') && !side.contains(event.target) && !toggle.contains(event.target)) setOpen(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && side.classList.contains('is-open')) { setOpen(false); toggle.focus(); }
  });
  const current = side.querySelector('.is-current');
  if (current && !mobile.matches) side.scrollTop = Math.max(0, current.offsetTop - side.clientHeight / 2);
});
