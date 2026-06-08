import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import OcrConsole from './pages/OcrConsole';
import Settings from './pages/Settings';
import ApiDocs from './pages/ApiDocs';
import Layout from './components/Layout';
import { useEffect, useState } from 'react';
import axios from 'axios';

// Ambient Background Component
const AmbientBackground = () => (
  <>
    <div className="ambient-blob bg-[#5e6ad2]" style={{ width: '40vw', height: '40vw', top: '-10%', left: '-10%', animationDelay: '0s' }} />
    <div className="ambient-blob bg-[#a853ba]" style={{ width: '30vw', height: '30vw', bottom: '-5%', right: '-5%', animationDelay: '-5s' }} />
    <div className="ambient-blob bg-[#2a8af6]" style={{ width: '25vw', height: '25vw', top: '40%', left: '40%', animationDelay: '-10s' }} />
  </>
);

function App() {
  const [isPublic, setIsPublic] = useState<boolean | null>(null);

  useEffect(() => {
    axios.get('/api/config').then(res => {
      setIsPublic(res.data.is_ocr_public);
    }).catch(() => {
      setIsPublic(true); // default fallback
    });
  }, []);

  if (isPublic === null) return <div className="min-h-screen flex items-center justify-center text-white">Loading...</div>;

  return (
    <BrowserRouter>
      <AmbientBackground />
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<Layout />}>
          <Route path="/" element={<OcrConsole isPublic={isPublic} />} />
          <Route path="/docs-ui" element={<ApiDocs />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
