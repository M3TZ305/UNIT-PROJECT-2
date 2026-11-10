/* Progressive atlas navigation. Content stays readable without JavaScript. */
(() => {
  'use strict';
  const atlas = document.querySelector('[data-atlas]');
  if (!atlas) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const group = atlas.querySelector('[data-atlas-tabs]');
  const controls = group?.querySelector('.atlas-tabs-controls');
  const tabs = [...(controls?.querySelectorAll('[data-tab-target]') || [])];
  const panels = [...(group?.querySelectorAll('[data-atlas-panel]') || [])];
  const art = group?.querySelector('[data-culture-art]');
  function activateTab(tab, focus = false) {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      const panel = panels.find(panel => panel.id === item.dataset.tabTarget);
      if (panel) panel.hidden = !active;
    });
    if (art) art.dataset.cultureArt = tab.dataset.art;
    if (focus) tab.focus();
  }
  if (tabs.length && panels.length) {
    controls.setAttribute('role', 'tablist');
    controls.hidden = false;
    tabs.forEach(tab => {
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', tab.dataset.tabTarget);
      const panel = panels.find(panel => panel.id === tab.dataset.tabTarget);
      if (panel) { panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', tab.id); panel.tabIndex = 0; }
      tab.addEventListener('click', () => activateTab(tab));
      tab.addEventListener('keydown', event => {
        const index = tabs.indexOf(tab);
        let next;
        if (event.key === 'ArrowLeft') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowRight') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (next !== undefined) { event.preventDefault(); activateTab(tabs[next], true); }
      });
    });
    activateTab(tabs[0]);
  }
  const links = [...atlas.querySelectorAll('.atlas-nav a')];
  const sections = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  const progress = atlas.querySelector('.atlas-reading-progress');
  let frame = 0;
  function followReading() {
    const limit = innerHeight * .3;
    const current = [...sections].reverse().find(section => section.getBoundingClientRect().top <= limit) || sections[0];
    links.forEach(link => {
      if (link.hash === '#' + current?.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    const box = atlas.getBoundingClientRect();
    const distance = box.height - innerHeight;
    if (progress) progress.style.setProperty('--reading-progress', Math.min(100, Math.max(0, -box.top / Math.max(1, distance) * 100)) + '%');
    frame = 0;
  }
  addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(followReading); }, { passive: true });
  addEventListener('resize', followReading);
  followReading();
  // A direct landmark link should expose its section, including on keyboard navigation.
  atlas.querySelectorAll('.atlas-annotation').forEach(link => link.addEventListener('click', () => {
    const target = document.getElementById(link.hash.slice(1));
    if (target) { target.tabIndex = -1; target.focus({ preventScroll: true }); }
  }));
  // The shared gallery owns modal navigation; keep the attribution in step with it.
  const creditsElement = document.getElementById('atlas-photo-credits');
  const gallery = document.querySelector('.atlas-gallery-dialog');
  if (creditsElement && gallery) {
    const credits = JSON.parse(creditsElement.textContent);
    const counter = gallery.querySelector('.gallery-counter');
    const credit = gallery.querySelector('[data-atlas-photo-credit]');
    const source = gallery.querySelector('[data-atlas-photo-source]');
    const update = () => {
      const index = Number(counter.textContent.split('/')[0].trim()) - 1;
      const entry = credits[index];
      if (!entry) return;
      credit.textContent = entry.author + ' · ' + entry.license;
      source.href = entry.source;
    };
    new MutationObserver(update).observe(counter, { childList: true, characterData: true, subtree: true });
  }
})();
