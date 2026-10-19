(function () {
  "use strict";

  var GAP = 8;

  function place(anchor) {
    var hint = anchor.querySelector(":scope > .hint");
    if (!hint) {
      return;
    }
    hint.classList.remove("hint-above");
    var box = anchor.getBoundingClientRect();
    var below = window.innerHeight - box.bottom;
    var needed = hint.offsetHeight + GAP;
    if (below < needed && box.top > below) {
      hint.classList.add("hint-above");
    }
  }

  function onEnter(event) {
    var anchor = event.target.closest && event.target.closest(".hint-anchor");
    if (anchor) {
      place(anchor);
    }
  }

  document.addEventListener("mouseover", onEnter);
  document.addEventListener("focusin", onEnter);
})();
