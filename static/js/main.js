(() => {
  'use strict';
  const messages = JSON.parse(document.getElementById('site-messages')?.textContent || '{}');
  const tr = text => messages[text] || text;
  const isRTL = document.documentElement.dir === 'rtl';
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

  // Only one pathway responds at a time; focus and pointer share the same state.
  const pathways = [...document.querySelectorAll('.th-pathway')];
  const activatePathway = selected => pathways.forEach(card => {
    card.classList.toggle('is-exploring', card === selected);
  });
  pathways.forEach(card => {
    card.addEventListener('pointerenter', event => {
      if (event.pointerType !== 'touch') activatePathway(card);
    });
    card.addEventListener('pointerleave', () => {
      activatePathway(card.matches(':focus-visible') ? card : null);
    });
    card.addEventListener('focus', () => activatePathway(card));
    card.addEventListener('blur', () => activatePathway(null));
  });

  // Changing a category or region keeps the other GET fields and lands at results.
  document.querySelectorAll('[data-filter-form]').forEach(form => {
    form.addEventListener('change', event => {
      if (event.target.matches('select[name="region"], select[name="province"], select[name="category"], input[name="category"]')) {
        form.requestSubmit();
      }
    });
  });

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
          button.setAttribute('aria-label', result.theme === 'dark' ? tr("تفعيل الوضع النهاري") : tr("تفعيل الوضع الليلي"));
          const browserColor = getComputedStyle(document.body).getPropertyValue('--browser-theme').trim();
          document.querySelector('meta[name="theme-color"]')?.setAttribute('content', browserColor || (result.theme === 'dark' ? '#211b21' : '#eae9e5'));
        };
        if (document.startViewTransition && !reduced) document.startViewTransition(apply); else apply();
      } catch { announce(tr("تعذّر حفظ الوضع. جرّب مرة أخرى.")); }
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
          control.querySelector('.save-label').textContent = result.saved ? tr("محفوظة") : tr("احفظ الحكاية");
        });
        document.querySelectorAll('[data-saved-count]').forEach(counter => counter.textContent = result.count);
        announce(result.saved ? tr("حُفظت الحكاية. تجدها في «حكاياتي».") : tr("أُزيلت المدينة من حكاياتك."));
        if (!result.saved && new URL(location.href).searchParams.get('saved') === '1') location.reload();
      } catch { announce(tr("تعذّر حفظ الحكاية. جرّب مرة أخرى.")); }
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
    const photoCredit = gallery.querySelector('[data-gallery-credit]');
    const photoSource = gallery.querySelector('[data-gallery-source]');
    if (photoCredit) photoCredit.textContent = galleryButtons[selected].dataset.photoCredit || '';
    if (photoSource) photoSource.href = galleryButtons[selected].dataset.photoSource || '#';
    gallery.querySelector('.gallery-counter').textContent = `${String(selected + 1).padStart(2, '0')} / ${String(galleryButtons.length).padStart(2, '0')}`;
  }
  galleryButtons.forEach((button, index) => button.addEventListener('click', () => {
    showImage(index); gallery.showModal();
  }));
  gallery?.querySelector('.gallery-prev').addEventListener('click', () => showImage(selected - 1));
  gallery?.querySelector('.gallery-next').addEventListener('click', () => showImage(selected + 1));
  gallery?.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') { event.preventDefault(); showImage(selected + (isRTL ? 1 : -1)); }
    if (event.key === 'ArrowRight') { event.preventDefault(); showImage(selected + (isRTL ? -1 : 1)); }
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

  document.querySelectorAll('[data-region-picker]').forEach(picker => {
    const trigger = picker.querySelector('summary');
    const links = [...picker.querySelectorAll('.region-picker-panel a')];
    const closePicker = () => { picker.open = false; trigger.focus(); };
    picker.addEventListener('keydown', event => {
      if (event.key === 'Escape' && picker.open) {
        event.preventDefault(); closePicker(); return;
      }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); picker.open = true;
      const current = links.indexOf(document.activeElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? links.length - 1
        : event.key === 'ArrowDown' ? (current + 1) % links.length
        : (current - 1 + links.length) % links.length;
      links[next].focus();
    });
    document.addEventListener('click', event => {
      if (picker.open && !picker.contains(event.target)) picker.open = false;
    });
  });

})();


/* Align deep links after disclosures open, using the actual sticky navigation height. */
(() => {
  const sticky = document.querySelector('.atlas-nav, .topic-switcher');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const offset = () => {
    if (!sticky) return 24;
    const position = getComputedStyle(sticky).position;
    return (position === 'sticky' || position === 'fixed' ? sticky.getBoundingClientRect().height : 0) + 24;
  };
  function targetFor(hash) {
    try { return document.getElementById(decodeURIComponent(hash.slice(1))); }
    catch { return null; }
  }
  function navigate(hash, focus = false, animate = false) {
    const target = targetFor(hash);
    if (!target) return false;
    target.closest('[data-atlas]')?.dispatchEvent(new CustomEvent('taleed:activate', { detail: target }));
    for (let node = target; node && node !== document.body; node = node.parentElement) {
      if (node.matches('details')) node.open = true;
    }
    target.classList.add('is-visible');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const destination = target.matches('.place-view-panel') ? target.closest('.place-view-stage') || target : target;
      const top = Math.max(0, destination.getBoundingClientRect().top + scrollY - offset());
      window.scrollTo({ top, behavior: animate && !reduced.matches ? 'smooth' : 'instant' });
      if (focus) {
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    }));
    return true;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search || !url.hash || !targetFor(url.hash)) return;
    event.preventDefault();
    if (location.hash !== url.hash) history.pushState(null, '', url.hash);
    navigate(url.hash, true, true);
  });
  addEventListener('hashchange', () => navigate(location.hash));
  const initial = () => {
    if (!location.hash) return;
    Promise.resolve(document.fonts?.ready).then(() => navigate(location.hash));
  };
  if (document.readyState === 'complete') initial();
  else addEventListener('load', initial, { once: true });
  if (sticky && 'ResizeObserver' in window) {
    new ResizeObserver(() => document.documentElement.style.setProperty('--anchor-offset', offset() + 'px')).observe(sticky);
  }
})();
