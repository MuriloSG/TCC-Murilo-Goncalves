(function () {
  "use strict";

  var panels = document.querySelectorAll("[data-notifications]");

  function applyFilter(panel) {
    var onlyUnread = panel.querySelector('[data-show="unread"]').getAttribute("aria-pressed") === "true";
    var visible = 0;
    panel.querySelectorAll(".notification").forEach(function (item) {
      var show = !onlyUnread || item.classList.contains("is-unread");
      item.hidden = !show;
      visible += show ? 1 : 0;
    });
    panel.querySelector("[data-empty]").hidden = visible > 0;
  }

  panels.forEach(function (panel) {
    var filter = panel.querySelector("[data-filter]");
    if (!filter) {
      return;
    }
    filter.hidden = false;
    filter.querySelectorAll("button").forEach(function (button) {
      button.addEventListener("click", function () {
        filter.querySelectorAll("button").forEach(function (other) {
          other.setAttribute("aria-pressed", String(other === button));
        });
        applyFilter(panel);
      });
    });
  });
})();
