import { useAuth } from "./auth.jsx";
import { Navigate } from "react-router-dom";

export default function Protected({ children }) {
  const { user } = useAuth();

  if (user === undefined) {
    return <div>Loading...</div>;
  }

  if (user === null) {
    // If not logged in → redirect to home or /auth
    return <Navigate to="/" replace />;
  }

  // If logged in successfully → render the protected page
  return children;
}