import { Routes, Route, Navigate} from 'react-router-dom';
import Home from './Home/Home';
import Form from './TypeForm/TypeForm';
import AuthOptions from './Home/AuthOptions';
import { AuthProvider } from "./auth";

function App() {
  return (
    <>
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/form" element={<Form />} />
        <Route path="/auth" element={<AuthOptions />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AuthProvider>
    </>
  );
}

export default App;
