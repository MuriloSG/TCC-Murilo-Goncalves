(function () {
  "use strict";

  function apply(group) {
    var source = document.getElementById(group.dataset.reveal);
    if (!source) {
      return;
    }
    group.querySelectorAll("[data-reveal-when]").forEach(function (block) {
      block.hidden = block.dataset.revealWhen !== source.value;
    });
  }

  document.querySelectorAll("[data-reveal]").forEach(function (group) {
    var source = document.getElementById(group.dataset.reveal);
    if (!source) {
      return;
    }
    apply(group);
    source.addEventListener("change", function () {
      apply(group);
    });
  });
})();
