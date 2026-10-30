import { animate, reducedMotion } from './motion';

const stage = document.querySelector<HTMLElement>('.demo-stage');
const tabs = [...document.querySelectorAll<HTMLButtonElement>('.video-choice')];
const panels = [...document.querySelectorAll<HTMLElement>('.video-panel')];
const routeNote = document.querySelector<HTMLElement>('#route-note');
const choices = document.querySelector<HTMLElement>('.video-choices');
const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
let selected = 0;
let frame = 0;

function resetSurface() {
  cancelAnimationFrame(frame);
  frame = 0;
  stage?.style.removeProperty('--tilt-x');
  stage?.style.removeProperty('--tilt-y');
  stage?.removeAttribute('data-hover');
}

function selectVideo(index: number, focus = false) {
  resetSurface();
  const changed = index !== selected;
  selected = index;
  tabs.forEach((tab, i) => {
    tab.setAttribute('aria-selected', String(i === index));
    tab.tabIndex = i === index ? 0 : -1;
  });
  panels.forEach((panel, i) => {
    panel.getAnimations().forEach(animation => animation.cancel());
    panel.hidden = i !== index;
    if (panel.hidden) panel.querySelector('video')?.pause();
  });
  const active = panels[index];
  if (routeNote) routeNote.hidden = active.dataset.kind !== 'recording';
  if (stage) stage.dataset.kind = active.dataset.kind;
  if (changed) animate(active, [
    { opacity: 0, transform: 'translateY(6px) scale(1.01)' },
    { opacity: 1, transform: 'translateY(0) scale(1)' },
  ], { duration: 360 });
  if (focus) {
    tabs[index].focus({ preventScroll: true });
    tabs[index].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
  }
}

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectVideo(index));
  tab.addEventListener('keydown', event => {
    let next = index;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = tabs.length - 1;
    else return;
    event.preventDefault();
    selectVideo(next, true);
  });
});

if (choices && panels.length) {
  choices.hidden = false;
  selectVideo(0);
}

stage?.addEventListener('pointermove', event => {
  const video = panels[selected]?.querySelector('video');
  if (reducedMotion.matches || !finePointer.matches || event.pointerType === 'touch' || !video?.paused) return;
  const rect = stage.getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
  // Keep the native playback controls still under the pointer.
  if (y > .82) { resetSurface(); return; }
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    stage.style.setProperty('--tilt-x', `${(0.5 - y) * 1.5}deg`);
    stage.style.setProperty('--tilt-y', `${(x - 0.5) * 1.5}deg`);
    stage.style.setProperty('--light-x', `${x * 100}%`);
    stage.style.setProperty('--light-y', `${y * 100}%`);
    stage.dataset.hover = 'true';
  });
});
stage?.addEventListener('pointerleave', resetSurface);
panels.forEach(panel => panel.querySelector('video')?.addEventListener('play', resetSurface));
reducedMotion.addEventListener('change', resetSurface);
finePointer.addEventListener('change', resetSurface);
document.addEventListener('visibilitychange', resetSurface);
