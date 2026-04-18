import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useStore } from "../store";
import { DomainSelector } from "./DomainSelector";
import { ThemeToggle } from "./ThemeToggle";
import { AccessibilityPanel } from "./AccessibilityPanel";

export function LoginView() {
  const ref = useStore((s) => s.applicantRef);
  const setRef = useStore((s) => s.setRef);
  const dob = useStore((s) => s.dob);
  const setDob = useStore((s) => s.setDob);
  const login = useStore((s) => s.login);
  const loading = useStore((s) => s.loading);
  const error = useStore((s) => s.error);
  const isLoggingIn = loading === "login";

  const rootRef = useRef<HTMLDivElement | null>(null);
  const mmRef = useRef<HTMLInputElement | null>(null);
  const yyyyRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!rootRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fade]",
        { opacity: 0, y: 14 },
        {
          opacity: 1,
          y: 0,
          duration: 0.65,
          ease: "power2.out",
          stagger: 0.07,
        },
      );
    }, rootRef);
    return () => ctx.revert();
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoggingIn) return;
    await login();
  };

  const autoAdvance = (
    current: HTMLInputElement,
    next: React.RefObject<HTMLInputElement | null>,
    maxLen: number,
  ) => {
    if (current.value.length >= maxLen && next.current) next.current.focus();
  };

  const inputBase =
    "mono w-full rounded-lg border hairline bg-surface px-4 py-3.5 text-base text-ink transition-all placeholder:text-ink-muted/60 focus:border-ink focus:outline-none";
  const segInput =
    "mono rounded-lg border hairline bg-surface px-2.5 py-3.5 text-center text-base focus:border-ink focus:outline-none";

  return (
    <section ref={rootRef} className="min-h-screen flex flex-col" aria-label="Sign in">
      <header
        className="flex items-center justify-between gap-3 px-8 pt-8 pb-6"
        data-fade
      >
        <div className="flex items-center gap-3">
          <div
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-full bg-ink"
          >
            <div className="h-2.5 w-2.5 rounded-full bg-cream" />
          </div>
          <div>
            <div className="display text-lg leading-none">Recourse</div>
            <div className="mt-1 text-[11px] uppercase leading-none tracking-[0.18em] text-ink-muted">
              Decision portal
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <AccessibilityPanel />
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center px-6 pb-16" id="main">
        <div className="w-full max-w-md">
          <div
            className="mb-5 text-xs uppercase tracking-[0.2em] text-ink-muted"
            data-fade
          >
            Your application portal
          </div>
          <h1 className="display mb-4 text-5xl leading-[1.02]" data-fade>
            Sign in to view your decision.
          </h1>
          <p className="mb-10 text-base leading-relaxed text-ink-muted" data-fade>
            Enter the reference number from the email we sent you, along with your date
            of birth. This link is bound to your case — nothing else will unlock it.
          </p>

          <form
            onSubmit={onSubmit}
            className="space-y-6"
            data-fade
            aria-describedby="login-legal"
          >
            <div>
              <label
                htmlFor="ref-input"
                className="mb-2 block text-[11px] uppercase tracking-[0.18em] text-ink-muted"
              >
                Application reference
              </label>
              <input
                id="ref-input"
                value={ref}
                onChange={(e) => setRef(e.target.value.trim().slice(0, 32))}
                placeholder="RC-2024-A4F2-9E31"
                autoComplete="off"
                spellCheck={false}
                autoFocus
                aria-required="true"
                className={inputBase}
              />
            </div>

            <fieldset>
              <legend className="mb-2 block text-[11px] uppercase tracking-[0.18em] text-ink-muted">
                Date of birth
              </legend>
              <div className="flex gap-2" role="group" aria-label="Date of birth">
                <input
                  value={dob.day}
                  onChange={(e) => {
                    setDob("day", e.target.value.replace(/\D/g, "").slice(0, 2));
                    autoAdvance(e.target, mmRef, 2);
                  }}
                  placeholder="DD"
                  inputMode="numeric"
                  autoComplete="bday-day"
                  maxLength={2}
                  aria-label="Day of birth"
                  className={`${segInput} w-[72px]`}
                />
                <input
                  ref={mmRef}
                  value={dob.month}
                  onChange={(e) => {
                    setDob("month", e.target.value.replace(/\D/g, "").slice(0, 2));
                    autoAdvance(e.target, yyyyRef, 2);
                  }}
                  placeholder="MM"
                  inputMode="numeric"
                  autoComplete="bday-month"
                  maxLength={2}
                  aria-label="Month of birth"
                  className={`${segInput} w-[72px]`}
                />
                <input
                  ref={yyyyRef}
                  value={dob.year}
                  onChange={(e) => setDob("year", e.target.value.replace(/\D/g, "").slice(0, 4))}
                  placeholder="YYYY"
                  inputMode="numeric"
                  autoComplete="bday-year"
                  maxLength={4}
                  aria-label="Year of birth"
                  className={`${segInput} w-[108px]`}
                />
              </div>
            </fieldset>

            {error && (
              <div
                role="alert"
                className="rounded-md border border-accent/40 bg-accent/5 px-3 py-2 text-[13px] text-accent"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoggingIn}
              className="btn-primary w-full py-3.5"
              aria-busy={isLoggingIn}
            >
              {isLoggingIn ? (
                <>
                  <span className="spinner" aria-hidden />
                  <span>Looking up your case…</span>
                </>
              ) : (
                <span>Look up my case →</span>
              )}
            </button>
          </form>

          <DomainSelector />

          <div
            className="mt-10 space-y-4 border-t hairline pt-6"
            data-fade
            id="login-legal"
          >
            <p className="text-[12px] leading-relaxed text-ink-muted">
              Can't find your reference number? It's in the subject line of the email we
              sent to the address on your application.
            </p>
            <div className="flex items-center gap-4 text-[11px] uppercase tracking-[0.15em] text-ink-muted">
              <span>GDPR Art. 22(3)</span>
              <span className="h-1 w-1 rounded-full bg-line" aria-hidden />
              <span>DPDP §11</span>
              <span className="h-1 w-1 rounded-full bg-line" aria-hidden />
              <span>Right to contest</span>
            </div>
          </div>
        </div>
      </div>

      <footer
        className="flex items-center justify-between border-t hairline px-8 py-6 text-[11px] text-ink-muted"
        data-fade
      >
        <div>Recourse · Model decision contestation portal</div>
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-good" aria-hidden />
          Case-bound access · audit-sealed
        </div>
      </footer>
    </section>
  );
}
