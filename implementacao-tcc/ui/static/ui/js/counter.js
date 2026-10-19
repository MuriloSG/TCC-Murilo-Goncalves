(function () {
  "use strict";

  document.querySelectorAll("[data-counter]").forEach(function (counter) {
    var field = document.getElementById(counter.dataset.counter);
    var value = counter.querySelector("[data-counter-value]");
    if (!field || !value) {
      return;
    }
    field.addEventListener("input", function () {
      value.textContent = String(field.value.length);
    });
  });
})();
