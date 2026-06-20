import { useState } from "react";
import AppBrand from "@/components/AppBrand";
import Icon from "@/components/icons/Icon";
import { useAuth } from "@/auth/AuthContext";
import { useSystemUsernamePrefill } from "@/auth/useSystemUsernamePrefill";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";

export default function SignInPage() {
  const { signIn } = useAuth();
  const { showError } = useSnackbar();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useSystemUsernamePrefill(setUsername);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedUsername = username.trim();
    const trimmedPassword = password;
    if (!trimmedUsername || !trimmedPassword) {
      return;
    }

    setSubmitting(true);
    try {
      await signIn({
        username: trimmedUsername,
        password: trimmedPassword,
      });
    } catch (err) {
      showError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sign-in-page">
      <div className="sign-in-page__card">
        <div className="sign-in-page__brand">
          <AppBrand to={undefined} />
        </div>

        <form className="sign-in-page__form" onSubmit={handleSubmit}>
          <div className="sign-in-page__fields">
            <label className="form-field">
              <span className="form-field__label">Username</span>
              <input
                className="form-field__input"
                type="text"
                name="username"
                autoComplete="username"
                placeholder="Username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                disabled={submitting}
              />
            </label>

            <label className="form-field">
              <span className="form-field__label">Password</span>
              <div className="form-field__password">
                <input
                  className="form-field__input form-field__input--password"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  autoComplete="current-password"
                  placeholder="Password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  disabled={submitting}
                />
                <button
                  type="button"
                  className="form-field__password-toggle"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                  disabled={submitting}
                >
                  <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
                </button>
              </div>
            </label>
          </div>

          <button
            type="submit"
            className="btn btn--primary sign-in-page__submit"
            disabled={submitting || !username.trim() || !password}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
