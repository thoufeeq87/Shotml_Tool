// Results page: copy buttons, download buttons and the device-size preview toggle.
(function () {
  "use strict";

  function codeText(id) {
    return document.getElementById(id).textContent;
  }

  function copyText(text, button) {
    var original = button.textContent;
    var done = function () {
      button.textContent = "Copied!";
      setTimeout(function () { button.textContent = original; }, 1500);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done);
      return;
    }
    var area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
    done();
  }

  function downloadText(filename, text, mime) {
    var link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: mime + ";charset=utf-8" }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () { copyText(codeText(button.dataset.copy), button); });
  });

  document.querySelectorAll("[data-download]").forEach(function (button) {
    button.addEventListener("click", function () {
      downloadText(button.dataset.filename, codeText(button.dataset.download), button.dataset.mime);
    });
  });

  document.querySelectorAll("[data-preview]").forEach(function (preview) {
    var frame = preview.querySelector("iframe");
    var buttons = preview.querySelectorAll("[data-device]");
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        frame.style.width = button.dataset.device;
        buttons.forEach(function (other) {
          var active = other === button;
          other.setAttribute("aria-pressed", active ? "true" : "false");
          other.classList.toggle("nb-button-secondary", active);
          other.classList.toggle("nb-button-surface", !active);
        });
      });
    });
  });
})();
