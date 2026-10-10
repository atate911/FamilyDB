// The box everyone writes to her in (the form #ask, in the old markup or the new). Every part is a help, never a need: with scripts off
// the box still sends. It keeps an unsent draft in the tab's session storage (put back if the box comes
// back empty, forgotten once the thread shows it arrived), fills the box from the ways to start, sends
// the phone's position only while "Send where I am" is ticked, and looks again for an answer when the
// page says to (data-refresh), never while somebody is writing.
(function () {
  "use strict";
  var form = document.getElementById("ask");
  var box = form && form.querySelector('textarea[name="text"]');
  if (!box) return;

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
      // nothing kept; the box still holds it
    }
  }

  function words(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  // When the draft is the newest thing the family said in the thread, it arrived.
  var theirs = document.querySelectorAll(".said-them .said-text, .msg--mine .msg__text");
  var newest = theirs.length ? theirs[theirs.length - 1].textContent : "";
  var draft = kept();
  if (draft && newest && words(draft) === words(newest)) draft = "";
  if (!box.value.trim() && draft) box.value = draft;
  keep();
  box.addEventListener("input", keep);

  // Ctrl or Cmd+Enter sends; Enter alone is a new line.
  box.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
    event.preventDefault();
    if (form.requestSubmit) form.requestSubmit();
    else if (form.reportValidity()) form.submit();
  });

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

  // Search in the box: while a short name is typed, what the family has by that name opens from
  // under the box (data-find, the page's /api/find), before anything is sent. A sentence is a
  // message, so nothing is looked up for one. Code on the server, never a model.
  var finder = form.getAttribute("data-find");
  var holder = form.querySelector(".box");
  if (finder && holder && window.fetch) {
    var list = document.createElement("ul");
    list.className = "box-finds";
    list.id = "box-finds";
    list.hidden = true;
    list.setAttribute("aria-label", "Already here");
    holder.parentNode.insertBefore(list, holder.nextSibling);
    var waiting = null;
    var asked = "";

    var show = function (found) {
      list.textContent = "";
      found.forEach(function (one) {
        var item = document.createElement("li");
        var link = document.createElement("a");
        link.href = one.href;
        var title = document.createElement("span");
        title.className = "box-finds__t";
        title.textContent = one.label;
        var kind = document.createElement("span");
        kind.className = "box-finds__k";
        kind.textContent = one.kind;
        link.appendChild(title);
        link.appendChild(kind);
        item.appendChild(link);
        list.appendChild(item);
      });
      list.hidden = found.length === 0;
    };

    var look = function () {
      var typed = words(box.value);
      if (typed.length < 2 || typed.length > 40 || typed.split(" ").length > 4) {
        asked = "";
        show([]);
        return;
      }
      if (typed === asked) return;
      asked = typed;
      window
        .fetch(finder + "?q=" + encodeURIComponent(typed), {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        })
        .then(function (answer) {
          return answer.ok ? answer.json() : { found: [] };
        })
        .then(function (data) {
          if (asked === typed) show(data.found || []);
        })
        .catch(function () {
          show([]);
        });
    };

    box.addEventListener("input", function () {
      window.clearTimeout(waiting);
      waiting = window.setTimeout(look, 180);
    });
    box.addEventListener("keydown", function (event) {
      if (event.key === "Escape") show([]);
    });
  }

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
          if (!here.checked) return; // unticked while looking
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

  // Only a page drawn for a plain visit says to, so this never resends a form.
  var every = parseInt(form.getAttribute("data-refresh"), 10);
  if (every > 0) {
    window.setInterval(function () {
      if (document.activeElement !== box && !box.value.trim()) window.location.reload();
    }, every * 1000);
  }
})();
