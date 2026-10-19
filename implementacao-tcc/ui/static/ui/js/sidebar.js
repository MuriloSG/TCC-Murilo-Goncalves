(function () {
  "use strict";

  var button = document.querySelector("[data-sidebar-toggle]");
  var shell = document.querySelector(".app-shell");
  if (!button || !shell) {
    return;
  }

  function sync() {
    var collapsed = shell.classList.contains("is-collapsed");
    button.setAttribute("aria-expanded", String(!collapsed));
    button.setAttribute("aria-label", collapsed ? "Expandir menu lateral" : "Recolher menu lateral");
  }

  button.addEventListener("click", function () {
    var collapsed = shell.classList.toggle("is-collapsed");
    document.cookie = "menu_lateral=" + (collapsed ? "recolhido" : "expandido") + "; path=/; max-age=31536000; SameSite=Lax";
    sync();
  });

  shell.addEventListener("pointerover", place);
  shell.addEventListener("focusin", place);

  function place(event) {
    var item = event.target.closest(".side-nav a, .nav-group > summary");
    if (!item || !shell.classList.contains("is-collapsed")) {
      return;
    }
    var box = item.getBoundingClientRect();
    item.style.setProperty("--tooltip-top", box.top + box.height / 2 + "px");
    item.style.setProperty("--tooltip-left", box.right + 12 + "px");
  }

  button.hidden = false;
  sync();
})();
