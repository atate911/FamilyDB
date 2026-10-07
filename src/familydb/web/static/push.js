// Notifications on this device (familydb/push.py): turns them on or off for whoever is signed in,
// on the page that says so (/you). Without this script, or a browser that cannot, nothing is
// turned on and the page says why; everything else works as before.
(() => {
  const box = document.querySelector('[data-push]');
  if (!box) return;
  const state = box.querySelector('[data-push-state]');
  const on = box.querySelector('[data-push-on]');
  const off = box.querySelector('[data-push-off]');
  const say = (words) => { state.textContent = words; };
  const can = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  if (!can || !box.dataset.key) { say(box.dataset.unable); return; }

  const bytes = (text) => {
    const plain = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4);
    return Uint8Array.from(atob(plain), (c) => c.charCodeAt(0));
  };
  const text = (buffer) => btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const post = (url, fields) => fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ csrf: box.dataset.csrf, ...fields }),
  });
  const show = (turnedOn) => {
    on.hidden = turnedOn;
    off.hidden = !turnedOn;
    say(turnedOn ? box.dataset.isOn : box.dataset.isOff);
  };

  navigator.serviceWorker.register('/sw.js').then(async (registration) => {
    let current = await registration.pushManager.getSubscription();
    show(Boolean(current));
    on.addEventListener('click', async () => {
      if ((await Notification.requestPermission()) !== 'granted') { say(box.dataset.refused); return; }
      try {
        current = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: bytes(box.dataset.key),
        });
        const sent = await post(box.dataset.on, {
          endpoint: current.endpoint,
          p256dh: text(current.getKey('p256dh')),
          auth: text(current.getKey('auth')),
        });
        if (!sent.ok) throw new Error('not kept');
        show(true);
      } catch (error) {
        if (current) await current.unsubscribe();
        current = null;
        say(box.dataset.failed);
      }
    });
    off.addEventListener('click', async () => {
      if (current) {
        await post(box.dataset.off, { endpoint: current.endpoint });
        await current.unsubscribe();
        current = null;
      }
      show(false);
    });
  }).catch(() => say(box.dataset.unable));
})();
