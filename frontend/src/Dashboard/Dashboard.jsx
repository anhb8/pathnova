import { useAuth } from "../Auth/auth";

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      {user && (
        <div className="mt-4">
          <p>Welcome, {user.name || user.email}!</p>
          <button
            onClick={logout}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded"
          >
            Log Out
          </button>
        </div>
      )}
    </div>
  );
}