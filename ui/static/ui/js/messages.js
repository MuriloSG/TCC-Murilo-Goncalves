(function () {
  "use strict";

  var LIFETIME = 15000;

  function remove(alert, moveFocus) {
    var messages = alert.closest(".messages");
    var next = alert.nextElementSibling || alert.previousElementSibling;
    alert.remove();
    if (messages && !messages.children.length) {
      messages.remove();
    }
    if (!moveFocus) {
      return;
    }
    var target = next ? next.querySelector("[data-message-close]") : document.getElementById("conteudo");
    if (target) {
      target.focus();
    }
  }

  function dismiss(alert, moveFocus) {
    if (!alert.isConnected || alert.classList.contains("is-leaving")) {
      return;
    }
    alert.classList.add("is-leaving");
    var done = false;
    var finish = function () {
      if (!done) {
        done = true;
        remove(alert, moveFocus);
      }
    };
    alert.addEventListener("animationend", finish, { once: true });
    window.setTimeout(finish, 400);
  }

  function schedule(root) {
    root.querySelectorAll(".messages > .alert:not([data-message-timed])").forEach(function (alert) {
      alert.setAttribute("data-message-timed", "");
      window.setTimeout(function () {
        dismiss(alert, alert.contains(document.activeElement));
      }, LIFETIME);
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-message-close]");
    if (button) {
      dismiss(button.closest(".alert"), true);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-message-close]").forEach(function (button) {
      button.hidden = false;
    });
    schedule(document);
  });

  document.addEventListener("htmx:afterSettle", function () {
    document.querySelectorAll("[data-message-close]").forEach(function (button) {
      button.hidden = false;
    });
    schedule(document);
  });
})();
