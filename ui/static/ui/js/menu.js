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

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }
    var open = document.activeElement && document.activeElement.closest("details.menu[open]");
    closeMenus(null);
    if (open) {
      open.querySelector("summary").focus();
    }
  });
})();
