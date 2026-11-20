const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".site-nav");

menuButton?.addEventListener("click", () => {
  const isOpen = navigation.classList.toggle("is-open");
  menuButton.setAttribute("aria-expanded", String(isOpen));
  menuButton.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
});

navigation?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navigation.classList.remove("is-open");
    menuButton?.setAttribute("aria-expanded", "false");
    menuButton?.setAttribute("aria-label", "Open navigation");
  });
});

const revealItems = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12 });

  revealItems.forEach((item) => revealObserver.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

const demoContainer = document.querySelector("#workflow-demo");

function loadWorkflowDemo() {
  if (!demoContainer || demoContainer.querySelector("iframe")) return;

  const frame = document.createElement("iframe");
  frame.src = "https://prashantahd.github.io/WizExpert/docs/demo/";
  frame.title = "WizExpert interactive workflow demo";
  frame.loading = "lazy";
  frame.allow = "fullscreen";
  frame.referrerPolicy = "strict-origin-when-cross-origin";
  demoContainer.replaceChildren(frame);
}

document.querySelector("[data-load-demo]")?.addEventListener("click", loadWorkflowDemo);

document.querySelector("[data-demo-target]")?.addEventListener("click", () => {
  demoContainer?.scrollIntoView({ behavior: "smooth", block: "center" });
  loadWorkflowDemo();
});

document.querySelector("#year").textContent = new Date().getFullYear();
