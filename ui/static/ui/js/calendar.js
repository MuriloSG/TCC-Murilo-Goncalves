(function () {
  "use strict";

  var filtered = false;

  function scrollToToday(root) {
    var area = root.querySelector("[data-public-scroll]");
    var today = area && area.querySelector("#hoje");
    if (!today) {
      return;
    }
    var corner = area.querySelector(".timetable-corner");
    area.scrollLeft = today.offsetLeft - (corner ? corner.offsetWidth : 0);
  }

  function markEdges(area) {
    var frame = area.closest("[data-public-frame]");
    if (!frame) {
      return;
    }
    var rest = area.scrollWidth - area.clientWidth - area.scrollLeft;
    frame.classList.toggle("has-before", area.scrollLeft > 1);
    frame.classList.toggle("has-after", rest > 1);
  }

  function watchEdges(root) {
    var area = root.querySelector("[data-public-scroll]");
    if (!area) {
      return;
    }
    markEdges(area);
    if (area.dataset.watched) {
      return;
    }
    area.dataset.watched = "true";
    area.addEventListener("scroll", function () {
      markEdges(area);
    }, { passive: true });
  }

  function scrollToCalendar() {
    var calendar = document.querySelector("[data-public-calendar]");
    if (!calendar || !window.matchMedia("(max-width: 39.99rem)").matches) {
      return;
    }
    var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    calendar.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
  }

  function prepare(root) {
    scrollToToday(root);
    watchEdges(root);
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

  window.addEventListener("resize", function () {
    var area = document.querySelector("[data-public-scroll]");
    if (area) {
      markEdges(area);
    }
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    if (document.querySelector("[data-public-calendar]")) {
      filtered = event.detail.elt.matches("[data-public-form], [data-public-group]");
      setBusy(true);
    }
  });

  document.addEventListener("htmx:afterRequest", function () {
    setBusy(false);
  });

  document.addEventListener("htmx:afterSettle", function () {
    prepare(document);
    if (filtered) {
      filtered = false;
      scrollToCalendar();
    }
  });
})();
