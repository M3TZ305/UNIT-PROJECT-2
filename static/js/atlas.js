/* Progressive atlas navigation. Content stays readable without JavaScript. */
(() => {
  'use strict';
  const atlas = document.querySelector('[data-atlas]');
  if (!atlas) return;
  const nav = atlas.querySelector('.atlas-nav');
  const links = [...nav.querySelectorAll('a[href^="#"]')];
  const stage = document.createElement('div');
  stage.className = 'place-view-stage';
  stage.setAttribute('aria-label', nav.getAttribute('aria-label'));
  const overview = [atlas.querySelector('#place'), atlas.querySelector('.atlas-place-intro'), atlas.querySelector('.atlas-film')].filter(Boolean);
  const ids = ['time', 'landmarks', 'crafts', 'architecture', 'people', 'dress', 'dishes', 'governorates'];
  const panels = ids.map(id => document.getElementById(id)).filter(Boolean);
  // Extract nested culture panels before moving the people overview.
  const fruit = document.getElementById('fruits');
  const dishes = document.getElementById('dishes');
  if (fruit && dishes) dishes.append(fruit);
  panels.forEach(panel => {
    panel.classList.add('place-view-panel');
    panel.dataset.placePanel = panel.id;
    stage.append(panel);
  });
  const stageTitle = document.createElement('h2');
  stageTitle.className = 'place-view-stage-title';
  stage.prepend(stageTitle);
  atlas.insertBefore(nav, atlas.firstChild);
  nav.after(stage);
  // The opening stays a separate view; all other sections share this stage.
  const cover = overview[0];
  if (cover) stage.before(cover);
  const intro = overview[1];
  if (intro) stage.before(intro);
  atlas.classList.add('has-section-views');
  const landmarkGrid = atlas.querySelector('.atlas-landmarks');
  if (landmarkGrid) landmarkGrid.style.setProperty('--landmark-count', Math.min(5, landmarkGrid.children.length));

  function activate(target) {
    if (!target || !atlas.contains(target)) return;
    const panel = panels.find(candidate => candidate === target || candidate.contains(target));
    const opening = !panel && overview.some(candidate => candidate === target || candidate.contains(target));
    if (!panel && !opening) return;
    const current = panel?.id || 'place';
    stage.dataset.active = current;
    stageTitle.hidden = !panel?.matches('details');
    stageTitle.textContent = links.find(link => link.hash === '#' + current)?.textContent.trim() || ''; 
    overview.forEach(node => { node.hidden = !opening; });
    stage.hidden = opening;
    panels.forEach(node => {
      node.hidden = node !== panel;
      if (node === panel) {
        if (node.matches('details')) node.open = true;
        node.querySelectorAll('.reveal').forEach(child => child.classList.add('is-visible'));
        node.classList.add('is-visible');
      }
    });
    links.forEach(link => {
      if (link.hash === '#' + current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  atlas.addEventListener('taleed:activate', event => activate(event.detail));
  let initial;
  try { initial = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch {}
  activate(initial || cover);
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
