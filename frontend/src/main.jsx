import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider, useAuth } from './contexts/AuthContext.jsx'
import App from './App.jsx'
import LoginForm from './components/Auth/LoginForm.jsx'
import RegisterForm from './components/Auth/RegisterForm.jsx'
import './index.css'

function AuthWrapper() {
  const { isAuthenticated, isLoading, isInitialized, refreshFromStorage } = useAuth();
  const [showRegister, setShowRegister] = useState(false);

  useEffect(() => {
    refreshFromStorage();
  }, [refreshFromStorage]);

  if (!isInitialized || isLoading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return showRegister ? (
      <RegisterForm
        onRegisterSuccess={() => setShowRegister(false)}
        onSwitchToLogin={() => setShowRegister(false)}
      />
    ) : (
      <LoginForm
        onLoginSuccess={() => refreshFromStorage()}
        onSwitchToRegister={() => setShowRegister(true)}
      />
    );
  }

  return <App />;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <AuthWrapper />
    </AuthProvider>
  </StrictMode>,
)