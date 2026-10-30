import { animate, reducedMotion } from './motion';

const messages = document.documentElement.lang === 'zh-CN' ? {
  copied: '已复制', linkCopied: '文章链接已复制', linkFailed: '未能复制，请从地址栏复制文章链接',
  copyFromAddress: '请从地址栏复制', copyLink: '复制链接', bibtexCopied: 'BibTeX 已复制',
  copyManually: '请手动复制', bibtexFailed: '复制失败，请选择下方的 BibTeX 文本手动复制', copyBibtex: '复制 BibTeX',
} : {
  copied: 'Copied', linkCopied: 'Article link copied', linkFailed: 'Could not copy; copy the link from the address bar',
  copyFromAddress: 'Copy from the address bar', copyLink: 'Copy link', bibtexCopied: 'BibTeX copied',
  copyManually: 'Copy manually', bibtexFailed: 'Copy failed; select the BibTeX text below and copy it', copyBibtex: 'Copy BibTeX',
};

const videos = [...document.querySelectorAll<HTMLVideoElement>('video')];
videos.forEach(video => {
  video.addEventListener('play', () => videos.forEach(other => {
    if (other !== video) other.pause();
  }));
  const showError = () => {
    const message = video.closest('.video-panel')?.querySelector<HTMLElement>('.media-error');
    if (message) message.hidden = false;
  };
  video.addEventListener('error', showError);
  video.querySelector('source')?.addEventListener('error', showError);
});

const copy = document.querySelector<HTMLButtonElement>('#copy-link');
const copyStatus = document.querySelector<HTMLElement>('#copy-status');
if (copy && navigator.clipboard?.writeText) {
  copy.hidden = false;
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      copy.textContent = messages.copied;
      if (copyStatus) copyStatus.textContent = messages.linkCopied;
    } catch {
      if (copyStatus) copyStatus.textContent = messages.linkFailed;
      copy.textContent = messages.copyFromAddress;
    }
    window.setTimeout(() => { copy.textContent = messages.copyLink; }, 2500);
  });
}

const copyCitation = document.querySelector<HTMLButtonElement>('#copy-citation');
const citation = document.querySelector<HTMLElement>('#bibtex-citation');
const citationStatus = document.querySelector<HTMLElement>('#citation-status');
if (copyCitation && citation && navigator.clipboard?.writeText) {
  copyCitation.hidden = false;
  copyCitation.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(citation.textContent || '');
      copyCitation.textContent = messages.copied;
      if (citationStatus) citationStatus.textContent = messages.bibtexCopied;
    } catch {
      copyCitation.textContent = messages.copyManually;
      if (citationStatus) citationStatus.textContent = messages.bibtexFailed;
    }
    window.setTimeout(() => { copyCitation.textContent = messages.copyBibtex; }, 2500);
  });
}

const links = [...document.querySelectorAll<HTMLAnchorElement>('[data-toc-link]')];
const sections = [...new Set(links.map(link => link.hash.slice(1)))].map(id => document.getElementById(id)).filter((node): node is HTMLElement => !!node);
const progress = document.querySelector<HTMLProgressElement>('#reading-progress');
const progressLabel = document.querySelector('#progress-label');
const pageProgress = document.querySelector<HTMLElement>('#page-progress-fill');
const desktopToc = document.querySelector<HTMLElement>('.article-sidebar .toc');
const articleElement = document.querySelector<HTMLElement>('.feature-article');
let queued = false;
function updateReading() {
  queued = false;
  let current = sections[0]?.id;
  for (const section of sections) {
    if (section.getBoundingClientRect().top <= 160) current = section.id;
  }
  links.forEach(link => {
    if (link.hash === `#${current}`) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
  const activeLink = desktopToc?.querySelector<HTMLElement>('[aria-current]');
  if (desktopToc && activeLink) {
    const top = activeLink.getBoundingClientRect().top - desktopToc.getBoundingClientRect().top;
    desktopToc.style.setProperty('--toc-y', `${top}px`);
    desktopToc.style.setProperty('--toc-height', `${activeLink.offsetHeight}px`);
    desktopToc.classList.add('has-marker');
  }
  if (articleElement && progress && progressLabel) {
    const end = articleElement.offsetTop + articleElement.offsetHeight - innerHeight;
    const fraction = Math.min(1, Math.max(0, scrollY / Math.max(1, end)));
    const label = `${Math.round(fraction * 100)}%`;
    progress.value = fraction * 100;
    progress.textContent = label;
    progressLabel.textContent = label;
    if (pageProgress) pageProgress.style.transform = `scaleX(${fraction})`;
  }
}
function scheduleUpdate() {
  if (!queued) { queued = true; requestAnimationFrame(updateReading); }
}
addEventListener('scroll', scheduleUpdate, { passive: true });
addEventListener('resize', scheduleUpdate);
document.fonts.ready.then(updateReading);
updateReading();

const mobileContents = document.querySelector<HTMLDetailsElement>('.mobile-contents');
mobileContents?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  mobileContents.open = false;
}));

const dialog = document.querySelector<HTMLDialogElement>('#image-dialog');
const expanded = document.querySelector<HTMLImageElement>('#expanded-image');
const caption = document.querySelector<HTMLElement>('#image-caption');
if (dialog && expanded && caption && typeof dialog.showModal === 'function') {
  let thumbnail: HTMLImageElement | null = null;
  let closing = false;
  let openRequest = 0;
  function imageTransform() {
    if (!thumbnail || !expanded) return 'scale(.96)';
    const origin = thumbnail.getBoundingClientRect();
    const target = expanded.getBoundingClientRect();
    if (!target.width || !target.height || origin.bottom < 0 || origin.top > innerHeight) return 'scale(.96)';
    return `translate(${origin.left - target.left}px, ${origin.top - target.top}px) scale(${origin.width / target.width}, ${origin.height / target.height})`;
  }
  async function closeImage() {
    if (!dialog?.open || closing) return;
    closing = true;
    openRequest++;
    expanded?.getAnimations().forEach(animation => animation.cancel());
    dialog.classList.add('is-closing', 'is-animating');
    const transform = imageTransform();
    const closingMotion = expanded && animate(expanded, [
      { transform: 'none', opacity: 1 },
      { transform, opacity: .3 },
    ], { duration: 230, fill: 'forwards' });
    if (closingMotion) await closingMotion.finished.catch(() => {});
    dialog.close();
  }
  document.querySelectorAll<HTMLAnchorElement>('[data-zoom]').forEach(link => {
    link.addEventListener('click', async event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const request = ++openRequest;
      thumbnail = link.querySelector('img');
      expanded.src = link.href;
      expanded.alt = link.querySelector('img')?.alt || '';
      caption.textContent = link.closest('figure')?.querySelector('figcaption')?.textContent || '';
      await expanded.decode().catch(() => {});
      if (request !== openRequest) return;
      closing = false;
      dialog.classList.remove('is-closing');
      expanded.getAnimations().forEach(animation => animation.cancel());
      dialog.showModal();
      document.documentElement.classList.add('modal-open');
      dialog.classList.add('is-animating');
      const openingMotion = animate(expanded, [
        { transform: imageTransform(), opacity: .6 },
        { transform: 'none', opacity: 1 },
      ], { duration: 420 });
      if (openingMotion) await openingMotion.finished.catch(() => {});
      if (!closing) dialog.classList.remove('is-animating');
    });
  });
  dialog.addEventListener('close', () => {
    expanded.getAnimations().forEach(animation => animation.cancel());
    dialog.classList.remove('is-closing', 'is-animating');
    document.documentElement.classList.remove('modal-open');
    closing = false;
  });
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeImage(); });
  dialog.querySelector('form')?.addEventListener('submit', event => { event.preventDefault(); closeImage(); });
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeImage();
    }
  });
  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches && closing) dialog.close();
  });
}
