/**
 * LoginPage — replica el modal `#loginModal` de `index.html` (líneas
 * 724-750) como página de ruta completa `/login` (ver SPEC-010 §2, nota
 * de adaptación de layout: la landing de marketing detrás del modal no
 * forma parte de este feature).
 *
 * El selector de rol es COSMÉTICO (ADR-0017 D8): se preserva visualmente
 * pero no se envía en el request ni gatea el login — el rol real lo
 * decide el backend.
 */
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { getRedirectForRole } from '../auth/roleRedirect';

const ROLE_TABS = [
  { id: 'citogenetista', label: 'Citogenetista', icon: 'fa-user-md' },
  { id: 'supervisor', label: 'Supervisor', icon: 'fa-clipboard-list' },
  { id: 'admin', label: 'Administrador', icon: 'fa-cogs' },
] as const;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<(typeof ROLE_TABS)[number]['id']>('citogenetista');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(false);
    setSubmitting(true);
    try {
      const user = await login(email, password);
      const target = getRedirectForRole(user.role);
      if (target) {
        window.location.href = target;
      } else {
        navigate('/', { replace: true });
      }
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="biomed-login-page">
      <div className="biomed-login-card">
        <div className="biomed-login-header">
          <h3>
            <i className="fas fa-dna" aria-hidden="true" /> BIOMED UMSS
          </h3>
          <p>Iniciar Sesión</p>
        </div>
        <div className="biomed-login-body">
          {error && (
            <div className="biomed-banner biomed-banner--error" role="alert">
              ⚠️ Credenciales incorrectas
            </div>
          )}

          <div className="biomed-login-role-selector">
            {ROLE_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`biomed-login-role-option${selectedTab === tab.id ? ' selected' : ''}`}
                onClick={() => setSelectedTab(tab.id)}
                data-testid={`role-tab-${tab.id}`}
              >
                <i className={`fas ${tab.icon}`} aria-hidden="true" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="loginUser">
                Usuario
              </label>
              <input
                id="loginUser"
                type="text"
                className="biomed-form-input"
                placeholder="Ingrese su usuario"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="loginPass">
                Contraseña
              </label>
              <input
                id="loginPass"
                type="password"
                className="biomed-form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button
              type="submit"
              className="biomed-btn biomed-btn--primary biomed-login-submit"
              disabled={submitting}
            >
              {submitting ? 'Ingresando…' : 'Ingresar al Sistema'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
