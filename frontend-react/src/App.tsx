import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './components/HomePage';
import { MarketplacePage } from './pages/MarketplacePage';
import { DashboardPage } from './pages/DashboardPage';
import { PublisherDashboard } from './pages/PublisherDashboard';
import { AgentPublishWizard } from './pages/AgentPublishWizard';
import { AgentInstallPage } from './pages/AgentInstallPage';
import { DeploymentDashboard } from './pages/DeploymentDashboard';
import { AdminReviewDashboard } from './pages/AdminReviewDashboard';
import { AgentDetailPage } from './pages/AgentDetailPage';
import { SubscriptionPage } from './pages/SubscriptionPage';
import { SubscribersPage } from './pages/SubscribersPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { RolesPage } from './pages/RolesPage';
import { LicenseManagementPage } from './pages/LicenseManagementPage';
import { LoginPage } from './pages/LoginPage';
import { OrgRegistrationPage } from './pages/OrgRegistrationPage';
import './index.css';

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Layout with sidebar for authenticated pages
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 ml-[220px]">
        {children}
      </main>
    </div>
  );
}

function AppRoutes() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Public route */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/register-org"
        element={isAuthenticated ? <Navigate to="/" replace /> : <OrgRegistrationPage />}
      />

      {/* Protected routes */}
      <Route path="/" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <HomePage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/marketplace" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <MarketplacePage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <DashboardPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/publisher" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <PublisherDashboard />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/publisher/new" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <AgentPublishWizard />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/subscribers" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <SubscribersPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/agent/:agentId" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <AgentDetailPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/install/:agentId" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <AgentInstallPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/deployments" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <DeploymentDashboard />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/agents" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <AdminReviewDashboard />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <AdminDashboardPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/users" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <RolesPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/licenses" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <LicenseManagementPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/pricing" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <SubscriptionPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />

      {/* Catch all - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;

