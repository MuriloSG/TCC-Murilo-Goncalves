(function () {
  "use strict";

  var masks = {
    semester: function (value) {
      var digits = value.replace(/\D/g, "").slice(0, 5);
      if (digits.length <= 4) {
        return digits;
      }
      var term = digits.charAt(4);
      return digits.slice(0, 4) + "/" + (term === "1" || term === "2" ? term : "");
    }
  };

  document.addEventListener("input", function (event) {
    var field = event.target;
    var mask = field.dataset && masks[field.dataset.mask];
    if (mask) {
      field.value = mask(field.value);
    }
  });
})();
