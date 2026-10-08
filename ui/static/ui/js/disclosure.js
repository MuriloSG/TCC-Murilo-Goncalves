(function () {
  "use strict";

  function setup() {
    document.querySelectorAll("[data-disclosure]:not([data-disclosure-ready])").forEach(function (button) {
      var region = document.getElementById(button.getAttribute("aria-controls"));
      if (!region) {
        return;
      }
      button.setAttribute("data-disclosure-ready", "");
      region.hidden = true;
      button.hidden = false;
    });
  }

  function label(button, open) {
    var text = button.getAttribute(open ? "data-label-open" : "data-label-closed");
    button.setAttribute("aria-label", text);
    var tip = button.querySelector(".tip");
    if (tip) {
      tip.textContent = text;
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-disclosure]");
    if (!button) {
      return;
    }
    var region = document.getElementById(button.getAttribute("aria-controls"));
    if (!region) {
      return;
    }
    var open = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", open ? "true" : "false");
    region.hidden = !open;
    label(button, open);
  });

  document.addEventListener("DOMContentLoaded", setup);
  document.addEventListener("htmx:afterSettle", setup);
})();
