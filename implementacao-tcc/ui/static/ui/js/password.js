(function () {
  "use strict";

  function setup() {
    document.querySelectorAll("[data-password-toggle][hidden]").forEach(function (button) {
      if (document.getElementById(button.getAttribute("aria-controls"))) {
        button.hidden = false;
      }
    });
  }

  function show(button, input, visible) {
    input.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", visible ? "true" : "false");
    button.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-password-toggle]");
    if (!button) {
      return;
    }
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) {
      return;
    }
    show(button, input, input.type === "password");
    input.focus();
    var end = input.value.length;
    input.setSelectionRange(end, end);
  });

  document.addEventListener("submit", function (event) {
    event.target.querySelectorAll("[data-password-toggle]").forEach(function (button) {
      var input = document.getElementById(button.getAttribute("aria-controls"));
      if (input) {
        show(button, input, false);
      }
    });
  }, true);

  document.addEventListener("DOMContentLoaded", setup);
  document.addEventListener("htmx:afterSettle", setup);
})();
