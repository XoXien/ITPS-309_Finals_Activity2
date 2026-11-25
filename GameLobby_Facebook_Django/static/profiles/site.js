"use strict";

document.querySelectorAll("[data-open]").forEach((link) => {
  link.addEventListener("click", (event) => {
    const dialog = document.getElementById(link.dataset.open);
    if (!dialog || typeof dialog.showModal !== "function") return;
    event.preventDefault();
    dialog.showModal();
  });
});

document.querySelectorAll("dialog").forEach((dialog) => {
  dialog
    .querySelector("[data-close]")
    ?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    const outside =
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom;
    if (outside) dialog.close();
  });
});

document.querySelectorAll("[data-photo-input]").forEach((input) => {
  let objectUrl;
  input.addEventListener("change", () => {
    const form = input.closest("form");
    const preview = form?.querySelector("[data-preview]");
    const file = input.files?.[0];
    if (!preview || !file) return;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(file);
    preview.src = objectUrl;
    preview.hidden = false;
    preview
      .closest(".upload-preview")
      ?.querySelector("[data-placeholder]")
      ?.setAttribute("hidden", "");
  });
});

let toastTimer;
document.querySelectorAll("[data-copy-link]").forEach((link) => {
  link.addEventListener("click", async (event) => {
    if (!navigator.clipboard || !window.isSecureContext) return;
    event.preventDefault();
    try {
      await navigator.clipboard.writeText(link.dataset.copyLink);
      const toast = document.getElementById("toast");
      if (!toast) return;
      toast.textContent =
        "Profile link copied. You can share it with your class.";
      toast.hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        toast.hidden = true;
      }, 3500);
    } catch {
      window.prompt("Copy your profile link", link.dataset.copyLink);
    }
  });
});

document.querySelectorAll("[data-save-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = "Saving…";
    }
    form.setAttribute("aria-busy", "true");
  });
});
