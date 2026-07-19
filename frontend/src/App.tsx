import React from "react";
import { AuthProvider } from "./context/AuthContext";
import { AppRouter } from "./routes/router";

import { ToastProvider } from "./components/Toast";

const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRouter />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
