// Converter page: choose files, show previews and friendly messages, then send them.
(function () {
  "use strict";

  var ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];

  var form = document.getElementById("upload-form");
  if (!form) return;

  var maxFiles = Number(form.dataset.maxFiles);
  var maxMb = Number(form.dataset.maxMb);
  var input = document.getElementById("screenshots");
  var dropzone = document.getElementById("dropzone");
  var messages = document.getElementById("upload-messages");
  var previewArea = document.getElementById("preview-area");
  var previewCount = document.getElementById("preview-count");
  var previewGrid = document.getElementById("preview-grid");
  var button = document.getElementById("convert-button");
  var csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;

  var chosen = [];

  // --- Messages ---
  function showMessages(list) {
    messages.innerHTML = "";
    list.forEach(function (text) {
      var line = document.createElement("p");
      line.textContent = text;
      messages.appendChild(line);
    });
    messages.hidden = list.length === 0;
  }

  // --- Adding files with friendly checks ---
  function addFiles(fileList) {
    var problems = [];
    var tooMany = false;

    Array.prototype.forEach.call(fileList, function (file) {
      if (ALLOWED_TYPES.indexOf(file.type) === -1) {
        problems.push("“" + file.name + "” is not a PNG, JPG or WebP picture. Please choose a different file.");
      } else if (file.size > maxMb * 1024 * 1024) {
        problems.push("“" + file.name + "” is too big (" + (file.size / 1048576).toFixed(1) + " MB). Each picture must be " + maxMb + " MB or smaller.");
      } else if (chosen.length >= maxFiles) {
        tooMany = true;
      } else {
        chosen.push(file);
      }
    });

    if (tooMany) problems.push("You can upload up to " + maxFiles + " screenshots at a time. The extra ones were left out.");
    showMessages(problems);
    input.value = "";
    render();
  }

  // --- Previews ---
  function render() {
    previewGrid.querySelectorAll("img").forEach(function (img) { URL.revokeObjectURL(img.src); });
    previewGrid.innerHTML = "";

    chosen.forEach(function (file, index) {
      var item = document.createElement("li");
      item.className = "border bg-surface p-2";

      var img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.alt = "Preview of " + file.name;
      img.className = "h-28 w-full border object-cover object-top";

      var name = document.createElement("p");
      name.className = "mt-2 break-all text-xs font-medium";
      name.textContent = file.name;

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "nb-button nb-button-accent nb-button-small mt-2 w-full";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", "Remove " + file.name);
      remove.addEventListener("click", function () {
        chosen.splice(index, 1);
        showMessages([]);
        render();
      });

      item.appendChild(img);
      item.appendChild(name);
      item.appendChild(remove);
      previewGrid.appendChild(item);
    });

    previewArea.hidden = chosen.length === 0;
    previewCount.textContent = chosen.length + " of " + maxFiles + " chosen";
  }

  input.addEventListener("change", function () { addFiles(input.files); });

  ["dragenter", "dragover"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.add("nb-dropzone-active");
    });
  });
  ["dragleave", "drop"].forEach(function (name) {
    dropzone.addEventListener(name, function (event) {
      event.preventDefault();
      dropzone.classList.remove("nb-dropzone-active");
    });
  });
  dropzone.addEventListener("drop", function (event) { addFiles(event.dataTransfer.files); });

  // --- Sending ---
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (chosen.length === 0) return showMessages(["Please choose at least one screenshot first."]);

    var data = new FormData();
    chosen.forEach(function (file) { data.append("screenshots", file); });
    data.append("keep_images", form.querySelector("[name=keep_images]:checked").value);

    button.disabled = true;
    button.textContent = "Uploading...";

    fetch(form.dataset.startUrl, { method: "POST", body: data, headers: { "X-CSRFToken": csrf } })
      .then(function (response) {
        return response.json().then(function (body) { return { ok: response.ok, body: body }; });
      })
      .then(function (reply) {
        if (!reply.ok) throw new Error((reply.body.errors || []).join("\n") || "Something went wrong. Please try again.");
        window.location.href = reply.body.progress_url;
      })
      .catch(function (error) {
        showMessages(error.message.split("\n"));
        button.disabled = false;
        button.textContent = "Convert to HTML and CSS";
      });
  });

  // --- Confirm before deleting a kept batch ---
  document.querySelectorAll("form[data-confirm]").forEach(function (deleteForm) {
    deleteForm.addEventListener("submit", function (event) {
      if (!window.confirm(deleteForm.dataset.confirm)) event.preventDefault();
    });
  });

  render();
})();
