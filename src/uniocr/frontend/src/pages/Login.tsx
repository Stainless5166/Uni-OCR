import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ScanText, Lock, KeyRound, Loader2 } from 'lucide-react';

export default function Login() {
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const res = await axios.post('/api/auth/login', {
        password,
        totp_code: totpCode || null
      });
      localStorage.setItem('token', res.data.access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative z-10 p-4">
      <div className="glass-panel w-full max-w-md p-8 flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary to-purple-500 flex items-center justify-center shadow-xl mb-6">
          <ScanText className="text-white" size={32} />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">UniOCR</h1>
        <p className="text-white/50 mb-8 text-center">Secure console access</p>
        
        {error && (
          <div className="w-full bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg mb-6 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="w-full flex flex-col gap-4">
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
            <input
              type="password"
              placeholder="Admin Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="glass-input w-full pl-10"
              required
            />
          </div>
          
          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
            <input
              type="text"
              placeholder="2FA Code (If enabled)"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              className="glass-input w-full pl-10"
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="glass-button-primary w-full mt-4 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : 'Authenticate'}
          </button>
        </form>
      </div>
    </div>
  );
}
