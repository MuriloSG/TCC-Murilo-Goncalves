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

  function readAll() {
    panels.forEach(function (panel) {
      panel.querySelectorAll(".notification.is-unread").forEach(function (item) {
        item.classList.remove("is-unread");
        item.querySelectorAll(".notification-dot, .sr-only").forEach(function (mark) {
          mark.remove();
        });
      });
      panel.querySelectorAll(".notifications-count, .notifications-filter-count").forEach(function (count) {
        count.remove();
      });
      panel.querySelector("summary").setAttribute("aria-label", "Notificações");
      panel.querySelector("[data-read-all]").disabled = true;
      applyFilter(panel);
    });
  }

  panels.forEach(function (panel) {
    var readAllButton = panel.querySelector("[data-read-all]");
    var filter = panel.querySelector("[data-filter]");
    readAllButton.hidden = false;
    readAllButton.disabled = !panel.querySelector(".notification.is-unread");
    filter.hidden = false;

    readAllButton.addEventListener("click", readAll);
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
