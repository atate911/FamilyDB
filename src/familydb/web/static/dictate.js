// Speaking instead of typing: a mic beside each box on the page that takes words (a field
// marked data-dictate, which may name where its mic goes). It uses the browser's own speech
// recognition, so it asks no model and costs nothing; the words appear in the box as they are
// said, to be put right and sent as if typed. Nothing is sent until somebody presses the form's
// own button. The sound goes from the browser to its maker (Apple for Safari, Google for
// Chrome), never through FamilyDB, which is why the family can turn it off (web_dictation,
// General settings). A browser without it (Firefox), or with scripts off, shows no mic at all;
// a phone keyboard's own mic still works there.
(() => {
  "use strict";
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const fields = document.querySelectorAll("[data-dictate]");
  if (!Recognition || !fields.length) return;
  const icons = document.currentScript && document.currentScript.dataset.icons;
  const SVG = "http://www.w3.org/2000/svg";
  let listening = null; // the one recognition running, and the button that started it

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
    // What was in the box before: the words said go after it, with a space between.
    const before = field.value.replace(/\s+$/, "");
    const joined = (said) => (before ? before + " " : "") + said.trim();

    recognition.onresult = (event) => {
      let said = "";
      for (let i = 0; i < event.results.length; i += 1) said += event.results[i][0].transcript;
      field.value = joined(said);
      // As if typed: the box's own script keeps the draft and puts the ways to start away.
      field.dispatchEvent(new Event("input", { bubbles: true }));
    };
    recognition.onerror = (event) => {
      // Refused, or no speech service here: the mic would never work, so it goes.
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
      return; // already listening elsewhere, as a double tap can make it
    }
    listening = { recognition, button };
    button.setAttribute("aria-pressed", "true");
    button.classList.add("listening");
  }

  for (const field of fields) {
    const button = mic();
    // Beside the box, or where the box keeps its buttons (data-dictate names that place).
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
  // Leaving the page, or sending it, ends the listening.
  window.addEventListener("pagehide", stop);
  document.addEventListener("submit", stop, true);
})();
