import { useEffect } from "react";
import "./App.css";
import { useStore } from "./store";
import { Header } from "./components/Header";
import { AuditTrail } from "./components/AuditTrail";
import { DevBar } from "./components/DevBar";
import { LoginView } from "./components/LoginView";
import { Step1View } from "./components/Step1View";
import { Step2View } from "./components/Step2View";
import { Step3View } from "./components/Step3View";
import { Step4View } from "./components/Step4View";
import { ValidationOverlay } from "./components/ValidationOverlay";

export default function App() {
  const step = useStore((s) => s.step);
  const error = useStore((s) => s.error);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [step]);

  if (step === 0) {
    return (
      <>
        <LoginView />
        <DevBar />
      </>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <div
        className="mx-auto grid max-w-shell grid-cols-1 gap-12 px-6 py-10 lg:grid-cols-[1fr_360px] lg:px-8"
      >
        <main id="main" tabIndex={-1} aria-label="Contestation flow">
          {step === 1 && <Step1View />}
          {step === 2 && <Step2View />}
          {step === 3 && <Step3View />}
          {step === 4 && <Step4View />}
        </main>
        <AuditTrail />
      </div>
      {error && (
        <div
          role="alert"
          className="fixed right-4 bottom-20 z-50 rounded-lg border border-accent/40 bg-surface px-4 py-3 text-sm text-accent shadow-lg"
        >
          {error}
        </div>
      )}
      <ValidationOverlay />
      <DevBar />
    </div>
  );
}
