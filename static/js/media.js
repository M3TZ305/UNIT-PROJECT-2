document.documentElement.classList.add('js');
document.addEventListener('error', function (event) {
  const image = event.target;
  if (image instanceof HTMLImageElement && image.dataset.fallback && !image.dataset.triedFallback) {
    image.dataset.triedFallback = 'true';
    image.removeAttribute('srcset');
    image.removeAttribute('sizes');
    image.src = image.dataset.fallback;
  }
}, true);
