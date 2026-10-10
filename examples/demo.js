// The examples' forms (examples/export.py): each says, in a note at the foot of the screen, what it
// would have done on a real FamilyDB. Nothing is sent anywhere.
(function () {
  "use strict";
  var note = null;
  var timer = null;

  function say(words) {
    if (!note) {
      note = document.createElement("div");
      note.className = "demo-note";
      note.setAttribute("role", "status");
      document.body.appendChild(note);
    }
    note.textContent = words;
    note.hidden = false;
    window.clearTimeout(timer);
    timer = window.setTimeout(function () {
      note.hidden = true;
    }, 6000);
  }

  document.addEventListener(
    "submit",
    function (event) {
      var form = event.target;
      if (!form || form.tagName !== "FORM") return;
      event.preventDefault();
      say(form.getAttribute("data-demo") || "In the example nothing is saved or sent.");
    },
    true
  );
})();
