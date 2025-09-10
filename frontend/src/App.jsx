import { Routes, Route, Navigate} from 'react-router-dom';
import Home from './Home/Home';
import Form from './TypeForm/TypeForm';
import AuthOptions from './Auth/AuthOptions';
import { AuthProvider } from "./Auth/auth";
import Protected from "./Auth/Protected";
import Dashboard from './Dashboard/Dashboard';

function App() {
  return (
    <>
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/form" element={<Form />} />
        <Route path="/auth" element={<AuthOptions />} />
        <Route path="*" element={<Navigate to="/" />} />
        <Route path="/dashboard" element={
            <Protected>
              <Dashboard />
            </Protected>
          } />
      </Routes>
    </AuthProvider>
    </>
  );
}

export default App;
