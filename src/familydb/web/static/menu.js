// Closes the bar's <details> menu on a click elsewhere or Escape (which refocuses its button).
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
