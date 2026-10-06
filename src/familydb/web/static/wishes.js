// Drag a wish into place by its grip (docs/WISHES.md). Letting go sends the wish's own Move form with
// the new position, so the move goes through the same token and tool as a button. The grip sits outside
// the line's <summary>, so a drag never opens it.
(function () {
  "use strict";

  function place(list, card) {
    const cards = Array.from(list.querySelectorAll(":scope > .wish"));
    return cards.indexOf(card) + 1;
  }

  function start(event) {
    const handle = event.target.closest(".wish__grip");
    if (!handle) return;
    const card = handle.closest(".wish");
    const list = card && card.parentElement;
    if (!list || !list.classList.contains("wishes")) return;
    event.preventDefault();
    const before = place(list, card);
    card.classList.add("dragging");
    // On the document: moving the card would drop a pointer capture on the handle.
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
      const form = card.querySelector("form.wish__move");
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
