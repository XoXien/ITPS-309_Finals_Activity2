"use strict";
document.documentElement.classList.add("js");

document.querySelectorAll("[data-reveal]").forEach((button) => {
  const field = document.getElementById(button.dataset.reveal);
  const icon = button.querySelector("img");
  if (!field || !icon) return;
  const label =
    field.labels?.[0]?.textContent.trim().toLowerCase() || "password";
  button.addEventListener("click", () => {
    const visible = field.type === "password";
    field.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute("aria-label", (visible ? "Hide " : "Show ") + label);
    icon.src = visible ? icon.dataset.hideSrc : icon.dataset.showSrc;
  });
});

