(function () {
  "use strict";

  function closeMenus(except) {
    document.querySelectorAll("details.menu[open]").forEach(function (menu) {
      if (menu !== except) {
        menu.removeAttribute("open");
      }
    });
  }

  document.addEventListener("click", function (event) {
    closeMenus(event.target.closest("details.menu"));
  });

  function closeDrawer(drawer) {
    if (drawer.classList.contains("is-closing")) {
      return;
    }
    drawer.classList.add("is-closing");
    drawer.querySelector(".topbar-panel").addEventListener("animationend", function () {
      drawer.classList.remove("is-closing");
      drawer.removeAttribute("open");
      drawer.querySelector("summary").focus();
    }, { once: true });
  }

  document.querySelectorAll("details.topbar-menu").forEach(function (drawer) {
    var close = drawer.querySelector("[data-drawer-close]");
    close.hidden = false;
    close.addEventListener("click", function () {
      closeDrawer(drawer);
    });
    drawer.querySelector("summary").addEventListener("click", function (event) {
      if (drawer.open) {
        event.preventDefault();
        closeDrawer(drawer);
      }
    });
    drawer.addEventListener("toggle", function () {
      if (drawer.open) {
        close.focus();
      }
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }
    var drawer = document.querySelector("details.topbar-menu[open]");
    if (drawer) {
      closeDrawer(drawer);
      return;
    }
    var open = document.activeElement && document.activeElement.closest("details.menu[open]");
    closeMenus(null);
    if (open) {
      open.querySelector("summary").focus();
    }
  });
})();
