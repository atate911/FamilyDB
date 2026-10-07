// FamilyDB's service worker, only to show that she has written (familydb/push.py). It keeps
// nothing and fetches nothing. A notice never carries her words; it says she has a message and
// opens the chat. Nothing is shown while a FamilyDB page is in front of the person.
self.addEventListener('push', (event) => {
  let said = {};
  try { said = event.data ? event.data.json() : {}; } catch (error) { said = {}; }
  const url = typeof said.url === 'string' && said.url.startsWith('/') ? said.url : '/chat';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((pages) => {
      if (pages.some((page) => page.focused)) return undefined;
      return self.registration.showNotification(said.title || 'FamilyDB', {
        tag: said.tag || 'familydb',
        data: { url },
        icon: '/static/icon-192.png',
      });
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/chat';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((pages) => {
      const open = pages.find((page) => 'focus' in page);
      return open ? open.focus().then((page) => page.navigate(url)) : self.clients.openWindow(url);
    }),
  );
});
