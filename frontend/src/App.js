import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import { Login, Signup } from "./pages/Auth";
import { Techniques, TechniqueDetail } from "./pages/Techniques";
import Analyze from "./pages/Analyze";
import Legitimacy from "./pages/Legitimacy";
import Dashboard from "./pages/Dashboard";
import { ScamWall, NewScam, ScamDetail } from "./pages/ScamWall";
import AdminAffiliates from "./pages/AdminAffiliates";
import MonetizationGuide from "./pages/MonetizationGuide";
import PublicReport, { PublicReportsList } from "./pages/PublicReport";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Navbar />
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
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
