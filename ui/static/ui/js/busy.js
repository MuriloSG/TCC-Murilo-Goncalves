(function () {
  "use strict";

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches || !form.matches("[data-busy]")) {
      return;
    }
    var region = form.closest("[data-busy-region]");
    if (!region) {
      return;
    }
    region.setAttribute("aria-busy", "true");
    region.querySelectorAll("button").forEach(function (button) {
      button.disabled = true;
    });
    var status = region.querySelector("[data-busy-status]");
    if (status) {
      status.hidden = false;
    }
  });
})();
