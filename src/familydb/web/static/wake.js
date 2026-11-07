// A recipe is cooked from: "Keep the screen on" holds the phone awake while its steps are read, with
// the browser's own Screen Wake Lock. Nothing is sent anywhere. Drawn only where the browser can do
// it (with scripts off there is nothing to hold); let go when pressed again or the page is left, and
// taken again when the page comes back while it was wanted.
(function () {
  "use strict";
  if (!("wakeLock" in navigator)) return;
  var lock = null;
  var wanted = false;

  function shown() {
    var button = document.getElementById("wake-btn");
    if (button) button.setAttribute("aria-pressed", String(Boolean(lock)));
  }

  function take() {
    navigator.wakeLock.request("screen").then(function (held) {
      lock = held;
      held.addEventListener("release", function () { lock = null; shown(); });
      shown();
    }).catch(function () { lock = null; wanted = false; shown(); });
  }

  function draw() {
    var slot = document.getElementById("wake");
    if (!slot || slot.firstChild) return;
    var button = document.createElement("button");
    button.type = "button";
    button.id = "wake-btn";
    button.className = "chip wake__btn";
    button.textContent = "Keep the screen on";
    button.addEventListener("click", function () {
      if (lock) { wanted = false; lock.release(); }
      else { wanted = true; take(); }
    });
    slot.appendChild(button);
    slot.hidden = false;
    shown();
  }

  document.addEventListener("visibilitychange", function () {
    if (wanted && !lock && document.visibilityState === "visible") take();
  });
  document.addEventListener("fdb:swapped", draw);
  draw();
})();
