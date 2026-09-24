// The page's one script: where the phone is, sent with a chat message when "Send where I am" is
// ticked, so "what's open near here?" needs nothing typed. Nothing is asked of the browser, and
// nothing is sent, until someone ticks it; the box stays as they left it. Without this script
// there is no box, and suggestions start from home.
(function () {
  "use strict";
  var form = document.querySelector("form.ask");
  var box = form && form.querySelector('input[name="send_where"]');
  if (!box || !navigator.geolocation) return;
  var lat = form.querySelector('input[name="lat"]');
  var lon = form.querySelector('input[name="lon"]');
  var note = document.getElementById("where");
  document.getElementById("locate").hidden = false;

  function say(text) {
    if (note) note.textContent = text;
  }

  function forget() {
    lat.value = "";
    lon.value = "";
    say("");
  }

  function locate() {
    say("Finding where you are…");
    navigator.geolocation.getCurrentPosition(
      function (position) {
        if (!box.checked) return; // unticked while the phone was looking
        lat.value = position.coords.latitude.toFixed(5);
        lon.value = position.coords.longitude.toFixed(5);
        say("Where you are goes with this message.");
      },
      function () {
        forget();
        if (box.checked) say("The browser gave no position; suggestions start from home.");
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 }
    );
  }

  box.addEventListener("change", function () {
    if (box.checked) locate();
    else forget();
  });
  if (box.checked) locate();
})();
