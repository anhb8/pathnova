import { Routes, Route } from 'react-router-dom';
import Home from './Home/Home';
import Form from './TypeForm/TypeForm';

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/form" element={<Form />} />
      </Routes>
    </>
  );
}

export default App;
