// A form marked data-in-place (a tick, I'll handle it, Undo) is posted without leaving the page:
// the page that comes back replaces this one's main column, its row and its menu, so a tick keeps
// the place it was made in and the counts stay right. What was done says so in a note held at the
// foot of the screen, with its Undo, wherever the page is scrolled.
//
// The form is posted exactly as it would be (the same fields, its one-time token, from this page),
// so nothing new is trusted. With scripts off, or when anything goes wrong, it posts as usual and
// the server sends the page back at the next row (edits._then).
(function () {
  "use strict";
  if (!window.fetch || !window.DOMParser || !window.FormData || !window.URL) return;
  document.documentElement.classList.add("js-inplace");

  var SWAP = ["#main", "nav.row", ".side"];

  function samePage(url) {
    var there = new URL(url, location.href);
    return there.origin === location.origin && there.pathname === location.pathname && there.search === location.search;
  }

  function closer(note) {
    if (!note || note.querySelector(".flash__close")) return;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "flash__close";
    button.setAttribute("aria-label", "Close this note");
    button.textContent = "×";
    button.addEventListener("click", function () { note.remove(); });
    note.appendChild(button);
  }

  function settle(then) {
    var note = document.querySelector("#main .flash");
    closer(note);
    // Focus goes where the hand is working: the row the tick landed on, else the note (read out as a status).
    var row = then ? document.getElementById(then) : null;
    var next = row ? row.querySelector("button, a") : null;
    if (next) next.focus({ preventScroll: true });
    else if (note) note.focus({ preventScroll: true });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-in-place")) return;
    event.preventDefault();
    if (form.dataset.sending) return; // a second tap while the first is on its way
    form.dataset.sending = "1";
    var body = new FormData(form);
    var pressed = event.submitter;
    if (pressed && pressed.name) body.append(pressed.name, pressed.value);
    var then = body.get("then");
    // Read off the attribute: a list's form has a field named "action", which hides form.action.
    var address = new URL(form.getAttribute("action") || location.href, location.href).href;

    fetch(address, { method: "POST", body: body, credentials: "same-origin", redirect: "follow" })
      .then(function (response) {
        if (!response.ok) {
          location.assign(response.url);
          return null;
        }
        return response.text().then(function (html) { return { url: response.url, html: html }; });
      })
      .then(function (came) {
        if (came === null) return;
        var page = new DOMParser().parseFromString(came.html, "text/html");
        // The same page under another address (/lists and /lists/shopping) is drawn here and the address
        // follows; another kind of page is gone to, as the form would have (what it said is then lost).
        if (!samePage(came.url)) {
          if (page.body.className !== document.body.className) {
            location.assign(came.url);
            return;
          }
          history.replaceState(null, "", came.url);
        }
        SWAP.forEach(function (selector) {
          var here = document.querySelector(selector);
          var there = page.querySelector(selector);
          if (here && there) here.replaceWith(document.adoptNode(there));
        });
        settle(then);
      })
      .catch(function () {
        // Posted as usual; its one-time token keeps a change that did arrive from being made twice.
        delete form.dataset.sending;
        HTMLFormElement.prototype.submit.call(form);
      });
  });

  closer(document.querySelector("#main .flash"));
})();
