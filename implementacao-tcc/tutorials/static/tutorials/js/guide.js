(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var figure = event.target.closest("[data-guide-figure]");
    var image = figure && figure.querySelector("img");
    if (image && image.currentSrc) {
      figure.href = image.currentSrc;
    }
  });

  var panel = document.querySelector("[data-guide-nav]");
  if (!panel) {
    return;
  }
  var wide = window.matchMedia("(min-width: 64rem)");
  var current = panel.querySelector("[data-guide-current]");
  var links = Array.prototype.slice.call(panel.querySelectorAll("a[href^='#']"));
  var sections = links.map(function (link) {
    return document.getElementById(link.getAttribute("href").slice(1));
  });

  function fit() {
    panel.open = wide.matches;
  }

  function mark(index) {
    links.forEach(function (link, position) {
      if (position === index) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
    if (current) {
      current.textContent = index >= 0 ? links[index].textContent : "";
    }
  }

  function update() {
    var line = wide.matches ? window.innerHeight * 0.3 : window.innerHeight * 0.4;
    var index = -1;
    sections.forEach(function (section, position) {
      if (section && section.getBoundingClientRect().top <= line) {
        index = position;
      }
    });
    mark(index);
  }

  var pending = false;
  window.addEventListener("scroll", function () {
    if (!pending) {
      pending = true;
      window.requestAnimationFrame(function () {
        pending = false;
        update();
      });
    }
  }, { passive: true });

  links.forEach(function (link) {
    link.addEventListener("click", function () {
      if (!wide.matches) {
        panel.open = false;
      }
    });
  });

  wide.addEventListener("change", fit);
  fit();
  update();
})();
