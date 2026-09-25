(function () {
  "use strict";

  var root = document.documentElement;

  function sync() {
    var buttons = document.querySelectorAll("[data-expand]");
    if (!buttons.length) {
      root.classList.remove("is-expanded");
    }
    var expanded = root.classList.contains("is-expanded");
    buttons.forEach(function (button) {
      button.hidden = false;
      button.setAttribute("aria-pressed", expanded ? "true" : "false");
    });
  }

  function expand() {
    root.classList.add("is-expanded");
    sync();
    if (root.requestFullscreen && !document.fullscreenElement) {
      root.requestFullscreen({ navigationUI: "hide" }).catch(function () {});
    }
  }

  function collapse() {
    root.classList.remove("is-expanded");
    sync();
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(function () {});
    }
  }

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-expand]")) {
      if (root.classList.contains("is-expanded")) {
        collapse();
      } else {
        expand();
      }
    }
  });

  document.addEventListener("fullscreenchange", function () {
    if (!document.fullscreenElement && root.classList.contains("is-expanded")) {
      collapse();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !event.defaultPrevented && root.classList.contains("is-expanded") && !document.fullscreenElement && !document.querySelector("dialog[open], details[open]")) {
      collapse();
    }
  });

  document.body.addEventListener("htmx:afterSettle", sync);
  sync();
})();
