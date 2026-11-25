import { Menu, Moon, Sun, X } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { Skeleton, Wordmark } from "./components/ui";
import { load, save } from "./lib/storage";
import Landing from "./pages/Landing";

const Check = lazy(() => import("./pages/Check"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));
const Instructors = lazy(() => import("./pages/Instructors"));
const ClassDashboard = lazy(() => import("./pages/ClassDashboard"));
const Privacy = lazy(() => import("./pages/Privacy"));
const NotFound = lazy(() => import("./pages/NotFound"));

const NAV = [
  { to: "/check", label: "Check work" },
  { to: "/how-it-works", label: "How it works" },
  { to: "/instructors", label: "For instructors" },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<string | null>(() => load("redline.theme"));
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
  }, [theme]);
  const dark = theme ? theme === "dark" : window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return (
    <button
      type="button"
      onClick={() => {
        const next = dark ? "light" : "dark";
        setTheme(next);
        save("redline.theme", next);
      }}
      className="grid size-9 place-items-center rounded-lg text-ink-2 hover:bg-ink/5 hover:text-ink"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}

function Shell() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [loc.pathname]);
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-[15px] transition-colors ${isActive ? "text-ink font-medium" : "text-ink-2 hover:text-ink"}`;

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-ink focus:px-4 focus:py-2 focus:text-paper">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-rule bg-paper/90 backdrop-blur supports-[backdrop-filter]:bg-paper/75">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" aria-label="Redline home" className="rounded-md">
            <Wordmark />
          </Link>
          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={link}>
                {n.label}
              </NavLink>
            ))}
            <ThemeToggle />
          </nav>
          <div className="flex items-center gap-1 md:hidden">
            <ThemeToggle />
            <button
              type="button"
              className="grid size-10 place-items-center rounded-lg text-ink hover:bg-ink/5"
              aria-expanded={open}
              aria-controls="mobile-nav"
              aria-label={open ? "Close menu" : "Open menu"}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>
        {open && (
          <nav id="mobile-nav" aria-label="Main" className="border-t border-rule px-4 pb-3 pt-2 md:hidden">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={({ isActive }) => `${link({ isActive })} block`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main id="main" className="flex-1">
        <Suspense
          fallback={
            <div className="mx-auto max-w-6xl space-y-3 px-4 py-12 sm:px-6">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-96 max-w-full" />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-ink-2 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <ul className="flex flex-wrap gap-x-6 gap-y-1">
            <li>For learners 18+</li>
            <li>No accounts</li>
            <li>Photos never stored</li>
          </ul>
          <div className="flex gap-5">
            <Link to="/privacy" className="hover:text-ink">
              Privacy
            </Link>
            <Link to="/how-it-works" className="hover:text-ink">
              How it works
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Landing />} />
        <Route path="check" element={<Check />} />
        <Route path="how-it-works" element={<HowItWorks />} />
        <Route path="instructors" element={<Instructors />} />
        <Route path="class/:code" element={<ClassDashboard />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
