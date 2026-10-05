(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function markRevealTargets() {
    const selectors = [
      'section:not(.hero) .section-head',
      '.split > *',
      '.contest-wrap > *',
      '.pricing-table',
      '.cta-box',
      '.welcome > *',
      '.doc > *',
      '.contest-banner',
      '.cx-top',
      '.cx-tabs',
      '.cx-body'
    ];
    document.querySelectorAll(selectors.join(',')).forEach((el) => {
      if (!el.classList.contains('reveal')) el.classList.add('reveal');
    });

    document.querySelectorAll('.tracks-grid,.format-grid,.topic-grid,.checklist,.faq-list,.hero-stats').forEach((el) => {
      el.classList.add('stagger-children');
    });
  }

  function revealAll() {
    document.querySelectorAll('.reveal,.stagger-children').forEach((el) => el.classList.add('is-visible'));
  }

  document.addEventListener('DOMContentLoaded', () => {
    markRevealTargets();

    if (reduced || !('IntersectionObserver' in window)) {
      revealAll();
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: .12, rootMargin: '0px 0px -6% 0px' });

    document.querySelectorAll('.reveal,.stagger-children').forEach((el) => observer.observe(el));
  });
})();
