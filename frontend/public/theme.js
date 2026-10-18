// Runs before the app bundle so the first paint uses the right theme.
// Same rule as src/hooks/useTheme.tsx: the saved choice, else light (the default).
// An external file (not inline) because serve.json's CSP allows only 'self' scripts.
(function () {
  var theme = null;
  try {
    theme = localStorage.getItem("theme");
  } catch (e) {
    // storage unavailable (private mode): use the default
  }
  document.documentElement.classList.toggle("dark", theme === "dark");
})();
