import {
  BrowserRouter,
  HashRouter,
  Route,
  Routes,
  Navigate,
  useLocation,
} from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider, useAuth } from "@/lib/AuthContext";
import PageNotFound from "@/lib/PageNotFound";
import ScrollToTop from "@/components/ScrollToTop";
import ProtectedRoute from "@/components/ProtectedRoute";
import ServerUnreachable from "@/components/ServerUnreachable";
import LocalModeBar from "@/components/LocalModeBar";
import Home from "@/pages/Home";
import Sample from "@/pages/Sample";
import GetStarted from "@/pages/GetStarted";
import Workspace from "@/pages/Workspace";
import Settings from "@/pages/Settings";
import ProjectLayout from "@/components/app/ProjectLayout";
import StoryDevelop from "@/pages/StoryDevelop";
import StoryScore from "@/pages/StoryScore";
import FundPackage from "@/pages/FundPackage";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";

// The static build (GitHub Pages) uses hash routing. A static host has no way
// to rewrite /workspace to index.html, so a deep link or a refresh would 404;
// with hashes every route is served by the one index.html at the root.
const IS_STATIC = import.meta.env.VITE_CINEMAWIN_MODE === "static";
const Router = IS_STATIC ? HashRouter : BrowserRouter;

// Routes that render without a backend.
const STATIC_PREFIXES = ["/", "/sample", "/settings"];

const AppRoutes = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError, checkAppState } = useAuth();
  const location = useLocation();

  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isStaticRoute = STATIC_PREFIXES.includes(location.pathname);
  if (authError?.type === "server_unreachable" && !isStaticRoute) {
    return <ServerUnreachable message={authError.message} onRetry={checkAppState} />;
  }

  return (
    <>
      <LocalModeBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sample" element={<Sample />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/get-started" element={<GetStarted />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/project/:id" element={<ProjectLayout />}>
            <Route index element={<Navigate to="develop" replace />} />
            <Route path="develop" element={<StoryDevelop />} />
            <Route path="score" element={<StoryScore />} />
            <Route path="fund" element={<FundPackage />} />
          </Route>
        </Route>
        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <ScrollToTop />
        <AppRoutes />
      </Router>
      <Toaster />
    </AuthProvider>
  );
}
