import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import { Login, Signup, ForgotPassword, ResetPassword } from "./pages/Auth";
import { Techniques, TechniqueDetail } from "./pages/Techniques";
import Analyze from "./pages/Analyze";
import Legitimacy from "./pages/Legitimacy";
import Dashboard from "./pages/Dashboard";
import { ScamWall, NewScam, ScamDetail } from "./pages/ScamWall";
import AdminAffiliates from "./pages/AdminAffiliates";
import MonetizationGuide from "./pages/MonetizationGuide";
import PublicReport, { PublicReportsList } from "./pages/PublicReport";
import Pricing, { PricingSuccess } from "./pages/Pricing";
import Compare from "./pages/Compare";
import AdminDigest from "./pages/AdminDigest";
import Unsubscribe from "./pages/Unsubscribe";
import DeepAudit, { DeepAuditResult } from "./pages/DeepAudit";
import Verified from "./pages/Verified";
import Live from "./pages/Live";
import LiveSessionDetail from "./pages/LiveSessionDetail";
import PublicLiveReport from "./pages/PublicLiveReport";
import Dispute from "./pages/Dispute";
import AdminDisputes from "./pages/AdminDisputes";
import FromReddit from "./pages/FromReddit";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import EditorialStandards from "./pages/EditorialStandards";
import AdminDashboard from "./pages/AdminDashboard";
import AdminDisagreements from "./pages/AdminDisagreements";
import VerifyEmail from "./pages/VerifyEmail";
import VerifyEmailBanner from "./components/VerifyEmailBanner";
import Footer from "./components/Footer";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Navbar />
          <VerifyEmailBanner />
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              style: {
                background: "#0d0d0d",
                color: "#fff",
                border: "1px solid rgba(0,255,65,0.4)",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: "12px",
              },
            }}
          />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/techniques" element={<Techniques />} />
            <Route path="/techniques/:slug" element={<TechniqueDetail />} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/analyze" element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
            <Route path="/legitimacy" element={<ProtectedRoute><Legitimacy /></ProtectedRoute>} />
            <Route path="/scams" element={<ScamWall />} />
            <Route path="/scams/new" element={<ProtectedRoute><NewScam /></ProtectedRoute>} />
            <Route path="/scams/:id" element={<ScamDetail />} />
            <Route path="/admin/affiliates" element={<ProtectedRoute><AdminAffiliates /></ProtectedRoute>} />
            <Route path="/admin/guide" element={<ProtectedRoute><MonetizationGuide /></ProtectedRoute>} />
            <Route path="/report/:slug" element={<PublicReport />} />
            <Route path="/reports" element={<PublicReportsList />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/pricing/success" element={<PricingSuccess />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/admin/digest" element={<ProtectedRoute><AdminDigest /></ProtectedRoute>} />
            <Route path="/unsubscribe" element={<Unsubscribe />} />
            <Route path="/audit" element={<ProtectedRoute><DeepAudit /></ProtectedRoute>} />
            <Route path="/audit/result" element={<ProtectedRoute><DeepAuditResult /></ProtectedRoute>} />
            <Route path="/verified" element={<Verified />} />
            <Route path="/live" element={<ProtectedRoute><Live /></ProtectedRoute>} />
            <Route path="/live/sessions/:id" element={<ProtectedRoute><LiveSessionDetail /></ProtectedRoute>} />
            <Route path="/live-report/:slug" element={<PublicLiveReport />} />
            <Route path="/dispute" element={<Dispute />} />
            <Route path="/admin/disputes" element={<ProtectedRoute><AdminDisputes /></ProtectedRoute>} />
            <Route path="/r" element={<FromReddit />} />
            <Route path="/from-reddit" element={<FromReddit />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/editorial-standards" element={<EditorialStandards />} />
            <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
            <Route path="/admin/disagreements" element={<ProtectedRoute><AdminDisagreements /></ProtectedRoute>} />
          </Routes>
          <Footer />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
