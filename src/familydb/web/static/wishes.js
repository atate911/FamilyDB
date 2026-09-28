// Dragging a wish into place on her list (docs/WISHES.md). The page works without this: each
// wish opens to Top, Up and Down buttons, forms of their own. With it, the grip at the left of
// each line is shown and is a handle: press it, drag the line up or down, and let go; the wish's
// own Move form is sent with its new place, so the move goes through the same form, token and
// tool as a button's. The grip sits outside the line's <summary>, so a drag never opens it.
(function () {
  "use strict";

  function place(list, card) {
    const cards = Array.from(list.querySelectorAll(":scope > .wish"));
    return cards.indexOf(card) + 1;
  }

  function start(event) {
    const handle = event.target.closest(".wish-grip");
    if (!handle) return;
    const card = handle.closest(".wish");
    const list = card && card.parentElement;
    if (!list || !list.classList.contains("wishes")) return;
    event.preventDefault();
    const before = place(list, card);
    card.classList.add("dragging");
    // On the document, not the handle: moving the card in the page would drop a capture.

    function move(e) {
      const others = Array.from(list.querySelectorAll(":scope > .wish")).filter((c) => c !== card);
      const below = others.find((c) => {
        const box = c.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      list.insertBefore(card, below || null);
    }

    function stop() {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", stop);
      document.removeEventListener("pointercancel", stop);
      card.classList.remove("dragging");
      const after = place(list, card);
      if (after === before) return;
      const form = card.querySelector("form.wish-list-move");
      if (!form) return;
      const position = document.createElement("input");
      position.type = "hidden";
      position.name = "position";
      position.value = String(after);
      form.appendChild(position);
      form.submit();
    }

    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", stop);
    document.addEventListener("pointercancel", stop);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("ol.wishes").forEach(function (list) {
      list.classList.add("can-drag");
      list.addEventListener("pointerdown", start);
    });
  });
})();
