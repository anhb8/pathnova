import "./AuthOptions.css";
import googleIcon from "../assets/google.svg";

export default function AuthOptions() {
  const startGoogleLogin = () => {
    window.location.href = `${import.meta.env.VITE_API_BASE}/auth/google/start`;
  };

  return (
    <div className="auth">
      <header className="auth__header">
        <a className="auth__brand" href="/">
          <span className="auth__logo" aria-hidden="true">◆</span>
          <span className="auth__brandText">PathNova</span>
        </a>
      </header>

      <main className="auth__main">
        <section className="authCard" role="dialog" aria-labelledby="auth-title" aria-describedby="auth-desc">
          <h1 id="auth-title" className="authCard__title" style={{textAlign: "center"}}>Sign in</h1>
          <p id="auth-desc" className="authCard__subtitle" style={{textAlign: "center"}}>
            Choose a sign-in method to continue to your study plan.
          </p>

          <button className="btn btn--google" onClick={startGoogleLogin}>
            <img
              className="btn__icon"
              src={googleIcon}
              alt=""
              aria-hidden="true"
            />
            Continue with Google
          </button>

          <div className="authCard__divider">
            <span className="authCard__rule" />
            <span className="authCard__or">OR</span>
            <span className="authCard__rule" />
          </div>

          {/* Future providers */}
          <div className="authCard__providers">
            <button className="btn btn--neutral" disabled title="More options coming soon">
              More providers coming soon
            </button>
          </div>

          <p className="authCard__fineprint">
            By continuing, you agree to our <a href="#" onClick={(e)=>e.preventDefault()}>Terms</a> and{" "}
            <a href="#" onClick={(e)=>e.preventDefault()}>Privacy Policy</a>.
          </p>
        </section>
      </main>

      <footer className="auth__footer">
        <p>© {new Date().getFullYear()} PathNova, Inc.</p>
      </footer>
    </div>
  );
}