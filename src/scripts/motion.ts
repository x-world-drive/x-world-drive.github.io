export const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
export const easeOut = 'cubic-bezier(.16, 1, .3, 1)';
const running = new Set<Animation>();

export function animate(element: Element, frames: Keyframe[], options: KeyframeAnimationOptions) {
  if (reducedMotion.matches || typeof element.animate !== 'function') return;
  const animation = element.animate(frames, { easing: easeOut, ...options });
  running.add(animation);
  animation.finished.catch(() => {}).finally(() => running.delete(animation));
  return animation;
}

reducedMotion.addEventListener('change', () => {
  if (reducedMotion.matches) running.forEach(animation => animation.cancel());
});

if (scrollY < 80 && !location.hash) {
  const opening = document.querySelectorAll('.article-header > *');
  opening.forEach((element, index) => animate(element, [
    { opacity: 0, transform: 'translateY(16px)', filter: 'blur(3px)' },
    { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' },
  ], { duration: 700, delay: index * 65, fill: 'backwards' }));
}
