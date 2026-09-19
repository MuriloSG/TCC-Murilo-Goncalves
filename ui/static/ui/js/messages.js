(function () {
  "use strict";

  function remove(alert) {
    var messages = alert.closest(".messages");
    var next = alert.nextElementSibling || alert.previousElementSibling;
    alert.remove();
    if (messages && !messages.children.length) {
      messages.remove();
    }
    var target = next ? next.querySelector("[data-message-close]") : document.getElementById("conteudo");
    if (target) {
      target.focus();
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-message-close]");
    if (!button) {
      return;
    }
    var alert = button.closest(".alert");
    if (alert.classList.contains("is-leaving")) {
      return;
    }
    alert.classList.add("is-leaving");
    var done = false;
    var finish = function () {
      if (!done) {
        done = true;
        remove(alert);
      }
    };
    alert.addEventListener("animationend", finish, { once: true });
    window.setTimeout(finish, 400);
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-message-close]").forEach(function (button) {
      button.hidden = false;
    });
  });
})();
