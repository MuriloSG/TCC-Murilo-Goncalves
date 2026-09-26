(function () {
  "use strict";

  function scrollToToday(root) {
    var area = root.querySelector("[data-public-scroll]");
    var today = area && area.querySelector("#hoje");
    if (!today) {
      return;
    }
    var corner = area.querySelector(".timetable-corner");
    area.scrollLeft = today.offsetLeft - (corner ? corner.offsetWidth : 0);
  }

  function prepare(root) {
    scrollToToday(root);
  }

  function setBusy(busy) {
    var calendar = document.querySelector("[data-public-calendar]");
    if (calendar) {
      calendar.setAttribute("aria-busy", busy ? "true" : "false");
    }
    document.querySelectorAll("[data-public-form] button[type=submit]").forEach(function (button) {
      button.disabled = busy;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    prepare(document);
  });

  document.addEventListener("htmx:beforeRequest", function () {
    if (document.querySelector("[data-public-calendar]")) {
      setBusy(true);
    }
  });

  document.addEventListener("htmx:afterRequest", function () {
    setBusy(false);
  });

  document.addEventListener("htmx:afterSettle", function () {
    prepare(document);
  });
})();
