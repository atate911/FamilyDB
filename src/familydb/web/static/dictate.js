// A mic beside each [data-dictate] field, using the browser's own speech recognition: no model call,
// and nothing is sent until the form's own button is pressed. The sound goes from the browser to its
// maker, never through FamilyDB (hence the web_dictation setting). A browser without it, or with
// scripts off, shows no mic.
(() => {
  "use strict";
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const fields = document.querySelectorAll("[data-dictate]");
  if (!Recognition || !fields.length) return;
  const icons = document.currentScript && document.currentScript.dataset.icons;
  const SVG = "http://www.w3.org/2000/svg";
  let listening = null; // the recognition running, and its button

  function mic() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mic";
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-label", "Speak instead of typing");
    button.title = "Speak instead of typing";
    if (icons) {
      const svg = document.createElementNS(SVG, "svg");
      svg.setAttribute("class", "icon");
      svg.setAttribute("aria-hidden", "true");
      svg.setAttribute("focusable", "false");
      const use = document.createElementNS(SVG, "use");
      use.setAttribute("href", icons + "#i-mic");
      svg.appendChild(use);
      button.appendChild(svg);
    }
    return button;
  }

  function stop() {
    if (!listening) return;
    listening.recognition.stop();
  }

  function listen(field, button) {
    const recognition = new Recognition();
    recognition.lang = document.documentElement.lang || navigator.language || "en";
    recognition.interimResults = true;
    recognition.continuous = false;
    // The words said go after what the box held.
    const before = field.value.replace(/\s+$/, "");
    const joined = (said) => (before ? before + " " : "") + said.trim();

    recognition.onresult = (event) => {
      let said = "";
      for (let i = 0; i < event.results.length; i += 1) said += event.results[i][0].transcript;
      field.value = joined(said);
      // As if typed, so ask.js keeps the draft.
      field.dispatchEvent(new Event("input", { bubbles: true }));
    };
    recognition.onerror = (event) => {
      // Refused, or no speech service: the mic would never work.
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        for (const other of document.querySelectorAll("button.mic")) other.hidden = true;
      }
    };
    recognition.onend = () => {
      button.setAttribute("aria-pressed", "false");
      button.classList.remove("listening");
      if (listening && listening.recognition === recognition) listening = null;
      field.focus();
    };
    try {
      recognition.start();
    } catch (e) {
      return; // already listening, as a double tap can cause
    }
    listening = { recognition, button };
    button.setAttribute("aria-pressed", "true");
    button.classList.add("listening");
  }

  for (const field of fields) {
    const button = mic();
    // Beside the box, or in the slot data-dictate names.
    const slot = field.dataset.dictate && document.getElementById(field.dataset.dictate);
    if (slot) slot.appendChild(button);
    else field.insertAdjacentElement("afterend", button);
    field.closest(".field, form")?.classList.add("can-dictate");
    button.addEventListener("click", () => {
      const mine = listening && listening.button === button;
      stop();
      if (!mine && !field.disabled) listen(field, button);
    });
  }
  window.addEventListener("pagehide", stop);
  document.addEventListener("submit", stop, true);
})();
