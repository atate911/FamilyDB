// The menu in the bar is a <details>, so it opens and closes from its own button with scripts
// off. This closes it the way a menu is expected to close as well: on a click anywhere else, and
// on Escape, which hands the focus back to its button.
(() => {
  const open = () => document.querySelectorAll("details.menu[open]");
  document.addEventListener("click", (event) => {
    for (const menu of open()) {
      if (!menu.contains(event.target)) menu.open = false;
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    for (const menu of open()) {
      menu.open = false;
      menu.querySelector("summary")?.focus();
    }
  });
})();
