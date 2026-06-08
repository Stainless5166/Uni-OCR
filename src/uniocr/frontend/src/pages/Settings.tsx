import { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Globe, Lock, QrCode } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export default function Settings() {
  const [config, setConfig] = useState<any>(null);
  const [newPassword, setNewPassword] = useState('');
  const [setup2fa, setSetup2fa] = useState<any>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [passwordFor2fa, setPasswordFor2fa] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });

  const loadConfig = async () => {
    try {
      const res = await axios.get('/api/config');
      setConfig(res.data);
    } catch (err) {
      setMessage({ text: 'Failed to load settings. Please log in again.', type: 'error' });
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleTogglePublic = async () => {
    try {
      await axios.post('/api/config', { is_ocr_public: !config.is_ocr_public });
      setConfig({ ...config, is_ocr_public: !config.is_ocr_public });
      setMessage({ text: 'Visibility updated', type: 'success' });
    } catch (err) {
      setMessage({ text: 'Update failed', type: 'error' });
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/api/config', { new_password: newPassword });
      setNewPassword('');
      setMessage({ text: 'Password updated successfully', type: 'success' });
    } catch (err) {
      setMessage({ text: 'Failed to update password', type: 'error' });
    }
  };

  const handleInit2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/auth/2fa/setup', { password: passwordFor2fa });
      setSetup2fa(res.data);
      setPasswordFor2fa('');
      setMessage({ text: 'Scan the QR code and verify', type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Setup failed', type: 'error' });
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/api/auth/2fa/verify', { totp_code: verifyCode });
      setSetup2fa(null);
      setVerifyCode('');
      loadConfig();
      setMessage({ text: '2FA successfully enabled!', type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Verification failed', type: 'error' });
    }
  };

  if (!config) return <div className="p-6 text-white">Loading...</div>;

  return (
    <div className="flex flex-col h-full gap-6 p-6 max-w-4xl mx-auto w-full">
      <header>
        <h2 className="text-3xl font-bold text-white tracking-tight">System Settings</h2>
        <p className="text-white/50">Manage access control and security</p>
      </header>

      {message.text && (
        <div className={`p-4 rounded-xl border ${message.type === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Access Control */}
        <div className="glass-panel p-6 flex flex-col gap-4">
          <div className="flex items-center gap-3 text-white">
            <Globe className="text-primary" />
            <h3 className="text-xl font-bold">Access Control</h3>
          </div>
          <p className="text-white/60 text-sm">Control whether the OCR Console is available publicly or requires authentication.</p>
          
          <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 mt-2">
            <div>
              <p className="text-white font-medium">Public OCR Console</p>
              <p className="text-white/40 text-xs">If disabled, users must log in to use OCR.</p>
            </div>
            <button 
              onClick={handleTogglePublic}
              className={`w-14 h-8 rounded-full transition-all relative ${config.is_ocr_public ? 'bg-primary' : 'bg-white/20'}`}
            >
              <div className={`w-6 h-6 bg-white rounded-full absolute top-1 transition-all ${config.is_ocr_public ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </div>

        {/* Change Password */}
        <div className="glass-panel p-6 flex flex-col gap-4">
          <div className="flex items-center gap-3 text-white">
            <Lock className="text-primary" />
            <h3 className="text-xl font-bold">Admin Password</h3>
          </div>
          <p className="text-white/60 text-sm">Change the admin password used to access settings and private OCR.</p>
          
          <form onSubmit={handleChangePassword} className="flex gap-2 mt-2">
            <input 
              type="password" 
              placeholder="New Password" 
              className="glass-input flex-1"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
            />
            <button type="submit" className="glass-button-primary whitespace-nowrap">Update</button>
          </form>
        </div>

        {/* 2FA Setup */}
        <div className="glass-panel p-6 flex flex-col gap-4 md:col-span-2">
          <div className="flex items-center gap-3 text-white">
            <ShieldAlert className="text-primary" />
            <h3 className="text-xl font-bold">Two-Factor Authentication (2FA)</h3>
          </div>
          
          <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex items-center justify-between">
            <div>
              <p className="text-white font-medium">Status: {config.is_2fa_enabled ? <span className="text-green-400">Enabled</span> : <span className="text-yellow-400">Disabled</span>}</p>
              <p className="text-white/40 text-xs">Enhance security by requiring an authenticator code.</p>
            </div>
          </div>

          {!config.is_2fa_enabled && !setup2fa && (
            <form onSubmit={handleInit2FA} className="flex flex-col gap-3 mt-2 max-w-sm">
              <input 
                type="password" 
                placeholder="Current Admin Password" 
                className="glass-input"
                value={passwordFor2fa}
                onChange={e => setPasswordFor2fa(e.target.value)}
                required
              />
              <button type="submit" className="glass-button-primary flex items-center justify-center gap-2">
                <QrCode size={18} /> Enable 2FA
              </button>
            </form>
          )}

          {setup2fa && (
            <div className="flex flex-col md:flex-row gap-8 items-start mt-4 bg-white/5 p-6 rounded-xl border border-white/10">
              <div className="bg-white p-4 rounded-xl">
                <QRCodeSVG value={setup2fa.uri} size={150} />
              </div>
              <div className="flex-1">
                <h4 className="text-white font-bold mb-2">Scan this QR Code</h4>
                <p className="text-white/60 text-sm mb-4">Use Google Authenticator, Authy, or your preferred TOTP app.</p>
                <form onSubmit={handleVerify2FA} className="flex gap-2">
                  <input 
                    type="text" 
                    placeholder="Enter 6-digit code" 
                    className="glass-input flex-1"
                    value={verifyCode}
                    onChange={e => setVerifyCode(e.target.value)}
                    required
                  />
                  <button type="submit" className="glass-button-primary">Verify</button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
