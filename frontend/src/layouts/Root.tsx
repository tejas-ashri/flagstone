import { Outlet } from "react-router-dom";
import { AuthProvider } from "../auth/AuthProvider";
import { ToastProvider } from "../components/toast/ToastProvider";

// Providers live inside the router so they can use navigation hooks.
export function Root() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Outlet />
      </ToastProvider>
    </AuthProvider>
  );
}
