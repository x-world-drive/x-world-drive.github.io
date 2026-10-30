export function tooltip(host: HTMLElement) {
  const tip = document.createElement('div');
  tip.className = 'ifig-tip';
  tip.hidden = true;
  tip.setAttribute('aria-hidden', 'true');
  host.append(tip);
  const live = host.querySelector('output');
  return {
    show(text: string, event?: PointerEvent) {
      if (live) live.textContent = text;
      if (!event) return;
      const box = host.getBoundingClientRect();
      tip.textContent = text;
      tip.hidden = false;
      const x = Math.min(Math.max(event.clientX - box.left, tip.offsetWidth / 2 + 4), box.width - tip.offsetWidth / 2 - 4);
      tip.style.left = `${x}px`;
      tip.style.top = `${event.clientY - box.top}px`;
    },
    hide() {
      tip.hidden = true;
      if (live) live.textContent = '';
    },
  };
}
