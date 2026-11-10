(() => {
  'use strict';
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const toast = document.querySelector('.toast');
  let toastTimer;
  function announce(message) {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('is-visible');
    toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 3200);
  }

  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('site-nav');
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav?.classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nav?.classList.contains('is-open')) {
      nav.classList.remove('is-open');
      menu.setAttribute('aria-expanded', 'false');
      menu.focus();
    }
  });

  if ('IntersectionObserver' in window && !reduced) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -20px 0px' });
    document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
    document.documentElement.classList.add('has-reveals');
  }

  if (!reduced && window.matchMedia('(pointer:fine)').matches) {
    document.querySelectorAll('[data-parallax]').forEach(visual => {
      let frame;
      visual.addEventListener('pointermove', event => {
        cancelAnimationFrame(frame);
        const bounds = visual.getBoundingClientRect();
        const x = ((event.clientX - bounds.left) / bounds.width - .5) * 13;
        const y = ((event.clientY - bounds.top) / bounds.height - .5) * 10;
        frame = requestAnimationFrame(() => {
          visual.style.setProperty('--mx', x + 'px'); visual.style.setProperty('--my', y + 'px');
        });
      });
      visual.addEventListener('pointerleave', () => {
        cancelAnimationFrame(frame);
        visual.style.setProperty('--mx', '0px'); visual.style.setProperty('--my', '0px');
      });
    });
  }

  // Changing a category or region keeps the other GET fields and lands at results.
  document.querySelectorAll('[data-filter-form]').forEach(form => {
    form.addEventListener('change', event => {
      if (event.target.matches('select[name="region"], select[name="province"], select[name="category"], input[name="category"]')) {
        form.requestSubmit();
      }
    });
  });

  // Chapter anchors remain usable without JavaScript; active navigation follows reading.
  const cityChapters = [...document.querySelectorAll('[data-city-chapter]')];
  const chapterLinks = [...document.querySelectorAll('[data-chapter-link]')];
  const chapterJump = document.querySelector('[data-chapter-jump]');
  chapterJump?.addEventListener('change', () => {
    const section = document.getElementById('chapter-' + chapterJump.value);
    if (section) { history.replaceState(null, '', '#chapter-' + chapterJump.value); section.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }); }
  });
  if (cityChapters.length && 'IntersectionObserver' in window) {
    const cityObserver = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!visible.length) return;
      const slug = visible[0].target.dataset.cityChapter;
      chapterLinks.forEach(link => {
        if (link.dataset.chapterLink === slug) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
      if (chapterJump) chapterJump.value = slug;
      const activeLink = chapterLinks.find(link => link.dataset.chapterLink === slug);
      const rail = activeLink?.parentElement;
      if (activeLink && rail && rail.clientWidth) {
        const itemBox = activeLink.getBoundingClientRect();
        const railBox = rail.getBoundingClientRect();
        if (itemBox.left < railBox.left || itemBox.right > railBox.right) {
          rail.scrollBy({ left: itemBox.left - railBox.left - (railBox.width - itemBox.width) / 2, behavior: reduced ? 'auto' : 'smooth' });
        }
      }
    }, { rootMargin: '-20% 0px -50% 0px', threshold: 0 });
    cityChapters.forEach(section => cityObserver.observe(section));
  }

  async function postForm(form, submitter) {
    const data = new FormData(form);
    if (submitter?.name) data.set(submitter.name, submitter.value);
    const response = await fetch(form.action, { method: 'POST', body: data, credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('Request failed');
    return response.json();
  }

  document.querySelectorAll('.theme-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button');
      button.disabled = true;
      try {
        const result = await postForm(form, event.submitter || button);
        const apply = () => {
          document.documentElement.dataset.theme = result.theme;
          button.value = result.theme === 'dark' ? 'light' : 'dark';
          button.setAttribute('aria-label', result.theme === 'dark' ? 'تفعيل الوضع النهاري' : 'تفعيل الوضع الليلي');
          const browserColor = getComputedStyle(document.body).getPropertyValue('--browser-theme').trim();
          document.querySelector('meta[name="theme-color"]')?.setAttribute('content', browserColor || (result.theme === 'dark' ? '#211b21' : '#eae9e5'));
        };
        if (document.startViewTransition && !reduced) document.startViewTransition(apply); else apply();
      } catch { announce('تعذّر حفظ الوضع. جرّب مرة أخرى.'); }
      finally { button.disabled = false; }
    });
  });

  document.querySelectorAll('.save-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button');
      button.disabled = true;
      try {
        const result = await postForm(form, event.submitter);
        document.querySelectorAll('.save-form').forEach(other => {
          if (other.dataset.city !== result.slug) return;
          const control = other.querySelector('button');
          control.classList.toggle('is-saved', result.saved);
          control.setAttribute('aria-pressed', String(result.saved));
          control.querySelector('.save-symbol').textContent = result.saved ? '◆' : '◇';
          control.querySelector('.save-label').textContent = result.saved ? 'محفوظة' : 'احفظ الحكاية';
        });
        document.querySelectorAll('[data-saved-count]').forEach(counter => counter.textContent = result.count);
        announce(result.saved ? 'حُفظت الحكاية. تجدها في «حكاياتي».' : 'أُزيلت المدينة من حكاياتك.');
        if (!result.saved && new URL(location.href).searchParams.get('saved') === '1') location.reload();
      } catch { announce('تعذّر حفظ الحكاية. جرّب مرة أخرى.'); }
      finally { button.disabled = false; }
    });
  });

  const gallery = document.querySelector('.gallery-dialog');
  const galleryButtons = [...document.querySelectorAll('[data-gallery-index]')];
  let selected = 0;
  function showImage(index) {
    if (!gallery || !galleryButtons.length) return;
    selected = (index + galleryButtons.length) % galleryButtons.length;
    const source = galleryButtons[selected].querySelector('img');
    const image = gallery.querySelector('.lightbox-image');
    delete image.dataset.triedFallback;
    image.dataset.fallback = source.dataset.fallback;
    image.alt = source.alt; image.src = source.currentSrc || source.src;
    gallery.querySelector('.lightbox-caption').textContent = source.alt;
    gallery.querySelector('.gallery-counter').textContent = `${String(selected + 1).padStart(2, '0')} / ${String(galleryButtons.length).padStart(2, '0')}`;
  }
  galleryButtons.forEach((button, index) => button.addEventListener('click', () => {
    showImage(index); gallery.showModal();
  }));
  gallery?.querySelector('.gallery-prev').addEventListener('click', () => showImage(selected - 1));
  gallery?.querySelector('.gallery-next').addEventListener('click', () => showImage(selected + 1));
  gallery?.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') { event.preventDefault(); showImage(selected + 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); showImage(selected - 1); }
  });

  const videoDialog = document.querySelector('.video-dialog');
  document.querySelectorAll('[data-video-id]').forEach(button => button.addEventListener('click', () => {
    if (!videoDialog || !/^[A-Za-z0-9_-]{11}$/.test(button.dataset.videoId)) return;
    const frame = document.createElement('iframe');
    frame.src = 'https://www.youtube-nocookie.com/embed/' + button.dataset.videoId + '?autoplay=1&rel=0';
    frame.title = button.dataset.videoTitle;
    frame.allow = 'autoplay; encrypted-media; fullscreen; picture-in-picture';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    videoDialog.querySelector('.video-container').replaceChildren(frame);
    videoDialog.showModal();
  }));
  videoDialog?.addEventListener('close', () => videoDialog.querySelector('.video-container').replaceChildren());
  document.querySelectorAll('.media-dialog').forEach(dialog => {
    dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
  });

  const chapters = [...document.querySelectorAll('.chapter-nav a')];
  if (chapters.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        chapters.forEach(link => {
          if (link.hash === '#' + entry.target.id) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-10% 0px -55% 0px', threshold: 0 });
    chapters.forEach(link => { const section = document.querySelector(link.hash); if (section) observer.observe(section); });
  }
})();
