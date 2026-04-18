import { useStore } from "../store";

export function DevBar() {
  const step = useStore((s) => s.step);
  const goto = useStore((s) => s.goto);
  const signOut = useStore((s) => s.signOut);
  const login = useStore((s) => s.login);

  return (
    <nav
      aria-label="Demo rehearsal controls"
      className="fixed bottom-4 left-4 z-[100] flex items-center gap-2 rounded-full bg-ink px-3.5 py-2 text-[11px] uppercase tracking-wider text-cream/80 opacity-85 shadow-xl"
    >
      <span className="opacity-60" aria-hidden>DEMO</span>
      <button
        type="button"
        onClick={signOut}
        className="opacity-60 transition hover:opacity-100"
        aria-label="Jump to login screen"
      >
        login
      </button>
      <span className="h-2.5 w-px bg-cream/20" aria-hidden />
      {[1, 2, 3, 4].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => goto(n as 1 | 2 | 3 | 4)}
          aria-label={`Jump to step ${n}`}
          aria-current={step === n ? "step" : undefined}
          className={`transition hover:opacity-100 ${step === n ? "opacity-100" : "opacity-60"}`}
        >
          {n}
        </button>
      ))}
      <span className="h-2.5 w-px bg-cream/20" aria-hidden />
      <button
        type="button"
        onClick={() => login()}
        className="opacity-60 transition hover:opacity-100"
        aria-label="Log in immediately with stored demo credentials"
      >
        quick-login
      </button>
    </nav>
  );
}
