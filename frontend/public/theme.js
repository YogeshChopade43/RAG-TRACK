// Runs before the app bundle so the first paint uses the right theme.
// Same rules as src/hooks/useTheme.tsx: saved choice, else light OS preference, else dark.
// An external file (not inline) because serve.json's CSP allows only 'self' scripts.
(function () {
  var theme;
  try {
    theme = localStorage.getItem("theme");
  } catch (e) {
    theme = null;
  }
  if (theme !== "dark" && theme !== "light") {
    var prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    theme = prefersLight ? "light" : "dark";
  }
  document.documentElement.classList.toggle("dark", theme === "dark");
})();
