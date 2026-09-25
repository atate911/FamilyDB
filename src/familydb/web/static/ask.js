// The page's one script, for the box everyone writes to her in (form.ask, on Home and at the foot
// of the chat). Everything here is a help, never a need: with scripts off the box still sends and
// every page still works. It does what a browser gives to nothing else:
//
// - Keeps what is being written. An unsent message is kept in this tab as it is typed, and put
//   back if the box comes back empty: after a change of page, signing in again, the page looking
//   again for an answer, or a send that never arrived. It is forgotten once the conversation
//   shows it arrived, and the tab forgets it when it closes.
// - Fills the box from the ways to start under it, instead of fetching the page again, and puts
//   them away once something is written, so a tap never replaces a draft.
// - Sends where the phone is with a message while "Send where I am" is ticked, so "what's open
//   near here?" needs nothing typed. Nothing is asked of the browser, and nothing is sent, until
//   someone ticks it; the box stays as they left it. Without this script there is no box, and
//   suggestions start from home.
// - Looks again for an answer when the page says to (data-refresh) and the box is open, as the
//   meta refresh does with scripts off, but never while somebody is writing.
(function () {
  "use strict";
  var form = document.querySelector("form.ask");
  var box = form && form.querySelector('textarea[name="text"]');
  if (!box) return;

  // ---- What is being written ---------------------------------------------------------------
  var KEY = "familydb.draft";

  function kept() {
    try {
      return window.sessionStorage.getItem(KEY) || "";
    } catch (e) {
      return ""; // storage refused, as in some private windows: the box still works
    }
  }

  function keep() {
    try {
      if (box.value.trim()) window.sessionStorage.setItem(KEY, box.value);
      else window.sessionStorage.removeItem(KEY);
    } catch (e) {
      // nothing kept, and nothing lost that the box does not still hold
    }
  }

  function words(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  // The newest thing the family said in the thread: when it is what was kept, it arrived.
  var theirs = document.querySelectorAll(".said-them .said-text");
  var newest = theirs.length ? theirs[theirs.length - 1].textContent : "";
  var draft = kept();
  if (draft && newest && words(draft) === words(newest)) draft = "";
  if (!box.value.trim() && draft) box.value = draft;
  keep(); // whatever the box holds now, put back here or handed back by the page
  box.addEventListener("input", keep);

  // Ctrl+Enter, or Cmd+Enter on a Mac, sends; Enter alone starts a new line, as it always has.
  box.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
    event.preventDefault();
    if (form.requestSubmit) form.requestSubmit();
    else if (form.reportValidity()) form.submit();
  });

  // ---- Ways to start -----------------------------------------------------------------------
  var starters = document.querySelector(".starters");

  function tidy() {
    if (starters) starters.hidden = box.disabled || Boolean(box.value.trim());
  }

  if (starters) {
    starters.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest("[data-say]");
      if (!link || box.disabled) return;
      event.preventDefault();
      box.value = link.getAttribute("data-say");
      keep();
      tidy();
      box.focus();
      box.setSelectionRange(box.value.length, box.value.length);
    });
    box.addEventListener("input", tidy);
    tidy();
  }

  // ---- Where I am --------------------------------------------------------------------------
  var here = form.querySelector('input[name="send_where"]');
  if (here && navigator.geolocation) {
    var lat = form.querySelector('input[name="lat"]');
    var lon = form.querySelector('input[name="lon"]');
    var note = document.getElementById("where");
    document.getElementById("locate").hidden = false;

    var say = function (text) {
      if (note) note.textContent = text;
    };

    var forget = function () {
      lat.value = "";
      lon.value = "";
      say("");
    };

    var locate = function () {
      say("Finding where you are…");
      navigator.geolocation.getCurrentPosition(
        function (position) {
          if (!here.checked) return; // unticked while the phone was looking
          lat.value = position.coords.latitude.toFixed(5);
          lon.value = position.coords.longitude.toFixed(5);
          say("Where you are goes with this message.");
        },
        function () {
          forget();
          if (here.checked) say("The browser gave no position; suggestions start from home.");
        },
        { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 }
      );
    };

    here.addEventListener("change", function () {
      if (here.checked) locate();
      else forget();
    });
    if (here.checked) locate();
  }

  // ---- Looking again -----------------------------------------------------------------------
  // Only a page drawn for a plain visit says to, so this never sends a form again.
  var every = parseInt(form.getAttribute("data-refresh"), 10);
  if (every > 0) {
    window.setInterval(function () {
      if (document.activeElement !== box && !box.value.trim()) window.location.reload();
    }, every * 1000);
  }
})();
