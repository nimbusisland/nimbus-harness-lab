(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canvas = document.querySelector('#starfield');
  const orbit = document.querySelector('.orbit-signal');
  const trace = document.querySelector('.trace-progress');
  const zone = document.querySelector('.trajectory-shell');
  const number = document.querySelector('#state-number');
  const label = document.querySelector('#state-label');

  if (canvas) {
    const ctx = canvas.getContext('2d');
    let width = 0, height = 0, dpr = 1;
    let points = [];
    let pointerX = .5, pointerY = .5;

    const seedPoints = () => {
      const count = Math.min(100, Math.max(42, Math.floor(width * height / 18000)));
      points = Array.from({ length: count }, (_, i) => ({
        x: ((i * 83) % 997) / 997,
        y: ((i * 149) % 991) / 991,
        r: .35 + ((i * 17) % 11) / 10,
        a: .18 + ((i * 23) % 37) / 100
      }));
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(devicePixelRatio || 1, 2);
      width = rect.width; height = rect.height;
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seedPoints(); draw();
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const dx = reduced ? 0 : (pointerX - .5) * 12;
      const dy = reduced ? 0 : (pointerY - .5) * 8;
      for (const point of points) {
        ctx.beginPath();
        ctx.fillStyle = `rgba(226,235,232,${point.a})`;
        ctx.arc(point.x * width + dx * point.r, point.y * height + dy * point.r, point.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    addEventListener('pointermove', (event) => {
      pointerX = event.clientX / innerWidth; pointerY = event.clientY / innerHeight;
      if (!reduced) requestAnimationFrame(draw);
    }, { passive: true });
    addEventListener('resize', resize, { passive: true });
    resize();
  }

  const steps = [...document.querySelectorAll('.trace-step')];

  let ticking = false;
  const update = () => {
    document.body.classList.toggle('has-scrolled', scrollY > 18);
    const focusY = innerHeight * .48;
    const active = steps.reduce((nearest, step) => {
      const rect = step.getBoundingClientRect();
      const distance = Math.abs((rect.top + rect.height * .5) - focusY);
      return !nearest || distance < nearest.distance ? { step, distance } : nearest;
    }, null)?.step;
    if (active) {
      number.textContent = active.dataset.state;
      label.textContent = active.dataset.label;
    }
    if (orbit) {
      const hero = document.querySelector('.observatory-hero').getBoundingClientRect();
      const progress = reduced ? 1 : Math.max(.08, Math.min(1, 1 - hero.bottom / (innerHeight * 1.1)));
      orbit.style.strokeDashoffset = String(1 - progress);
    }
    if (trace && zone) {
      const rect = zone.getBoundingClientRect();
      const range = rect.height - innerHeight * .58;
      const progress = reduced ? 1 : Math.max(0, Math.min(1, (-rect.top + innerHeight * .25) / Math.max(1, range)));
      trace.style.strokeDashoffset = String(1 - progress);
    }
    ticking = false;
  };
  const requestUpdate = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
  addEventListener('scroll', requestUpdate, { passive: true });
  addEventListener('resize', requestUpdate, { passive: true });
  update();
})();
