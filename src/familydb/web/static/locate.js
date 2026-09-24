// The page's one script: where the phone is, sent with a chat message, so "what's open near
// here?" needs nothing typed. The browser asks first; without this script, or without leave,
// the page works as before and suggestions start from home.
(function () {
  "use strict";
  var form = document.querySelector("form.ask");
  if (!form || !navigator.geolocation) return;
  var lat = form.querySelector('input[name="lat"]');
  var lon = form.querySelector('input[name="lon"]');
  var note = document.getElementById("where");
  var started = false;

  function locate() {
    if (started) return;
    started = true;
    navigator.geolocation.getCurrentPosition(
      function (position) {
        lat.value = position.coords.latitude.toFixed(5);
        lon.value = position.coords.longitude.toFixed(5);
        if (note) note.textContent = "Sending where you are with this message.";
      },
      function () {
        started = false; // refused or timed out: try again next time, and say nothing
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 }
    );
  }

  // Ask when someone starts writing, not the moment the page opens; if leave was already given,
  // there is nothing to ask and the position can be fetched straight away.
  var text = form.querySelector("textarea");
  if (text) text.addEventListener("focus", locate);
  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: "geolocation" }).then(function (status) {
      if (status.state === "granted") locate();
    }, function () {});
  }
})();
