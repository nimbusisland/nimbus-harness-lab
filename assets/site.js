(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const root = document.documentElement;
  const orbit = document.querySelector('.orbit-path');
  const spine = document.querySelector('.spine-progress');
  const story = document.querySelector('.story-layout');

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('is-visible');
    });
  }, { threshold: 0.17, rootMargin: '0px 0px -8% 0px' });

  document.querySelectorAll('.reveal, .chapter').forEach((node) => revealObserver.observe(node));

  const update = () => {
    document.body.classList.toggle('has-scrolled', scrollY > 18);

    if (orbit) {
      const hero = document.querySelector('.home-hero');
      const rect = hero.getBoundingClientRect();
      const progress = reduce ? 1 : Math.max(0, Math.min(1, 1 - rect.bottom / (innerHeight * 1.25)));
      orbit.style.strokeDashoffset = String(1 - Math.max(.08, progress));
    }

    if (spine && story) {
      const rect = story.getBoundingClientRect();
      const range = rect.height - innerHeight * .48;
      const progress = reduce ? 1 : Math.max(0, Math.min(1, (-rect.top + innerHeight * .28) / Math.max(1, range)));
      spine.style.strokeDashoffset = String(1 - progress);
    }
    root.style.setProperty('--scroll-y', `${scrollY}px`);
  };

  let ticking = false;
  const requestUpdate = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { update(); ticking = false; });
  };

  addEventListener('scroll', requestUpdate, { passive: true });
  addEventListener('resize', requestUpdate, { passive: true });
  update();
})();
