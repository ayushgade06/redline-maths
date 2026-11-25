// Apply a saved theme before first paint (no flash). Storage may be blocked: ignore.
try { var t = localStorage.getItem("redline.theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
