import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("cs_token");
    if (!token) { setLoading(false); return; }
    api.get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem("cs_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("cs_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const signup = async (emailOrOpts, password, name) => {
    // Support both legacy 3-arg call (email, password, name) and an options
    // object (e.g. { email, password, name, signup_source })
    const payload =
      typeof emailOrOpts === "object"
        ? emailOrOpts
        : { email: emailOrOpts, password, name };
    const { data } = await api.post("/auth/signup", payload);
    localStorage.setItem("cs_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("cs_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
