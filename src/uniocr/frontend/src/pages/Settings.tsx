import { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Globe, Lock, QrCode, Key, Cpu, Trash2, Server, HardDrive, Network, Clock } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export default function Settings() {
  const [config, setConfig] = useState<any>(null);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  
  const [newPassword, setNewPassword] = useState('');
  const [setup2fa, setSetup2fa] = useState<any>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [passwordFor2fa, setPasswordFor2fa] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });

  const loadData = async () => {
    try {
      const [confRes, sysRes, keysRes] = await Promise.all([
        axios.get('/api/config'),
        axios.get('/api/system/info'),
        axios.get('/api/apikeys')
      ]);
      setConfig(confRes.data);
      setSystemInfo(sysRes.data);
      setApiKeys(keysRes.data);
    } catch (err) {
      setMessage({ text: 'Failed to load settings. Please log in again.', type: 'error' });
    }
  };

  useEffect(() => {
    loadData();
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
      loadData();
      setMessage({ text: '2FA successfully enabled!', type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Verification failed', type: 'error' });
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/apikeys', { name: newKeyName });
      setNewKeyName('');
      loadData();
      
      const rawKey = res.data.api_key;
      alert(`API Key Created!\n\nPlease save this key now. It will NEVER be shown again:\n\n${rawKey}`);
      
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Failed to create API key', type: 'error' });
    }
  };

  const handleDeleteApiKey = async (id: number) => {
    if (!confirm('Are you sure you want to revoke this key?')) return;
    try {
      await axios.delete(`/api/apikeys/${id}`);
      loadData();
    } catch (err) {
      setMessage({ text: 'Failed to revoke API key', type: 'error' });
    }
  };

  if (!config || !systemInfo) return <div className="p-6 text-white flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>;

  return (
    <div className="flex flex-col h-full gap-8 p-6 max-w-6xl mx-auto w-full overflow-y-auto custom-scrollbar">
      <header>
        <h2 className="text-3xl font-bold text-white tracking-tight">System Settings & Dashboard</h2>
        <p className="text-white/50 mt-1">Manage access control, security, and monitor system health</p>
      </header>

      {message.text && (
        <div className={`p-4 rounded-xl border ${message.type === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'}`}>
          {message.text}
        </div>
      )}

      {/* Section 1: System Status Dashboard */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center gap-3 text-white border-b border-white/10 pb-2">
          <Cpu className="text-primary" />
          <h3 className="text-xl font-bold">System Status</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Node Details */}
          <div className="glass-panel p-5 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-white/50 mb-1">
              <Server size={16} />
              <span className="text-xs font-bold uppercase tracking-wider">Node Details</span>
            </div>
            
            <div className="flex flex-col gap-4 h-full justify-between">
              <div>
                <p className="text-white font-medium text-lg">{systemInfo.os} {systemInfo.release}</p>
                <p className="text-white/60 text-sm">{systemInfo.arch}</p>
                <p className="text-white/40 text-xs mt-1">Python {systemInfo.python_version}</p>
              </div>
              
              <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-white/60 text-xs flex items-center gap-1"><Network size={12}/> Local IP</span>
                  <span className="text-white font-mono text-xs">{systemInfo.network_ip}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60 text-xs flex items-center gap-1"><Clock size={12}/> Uptime</span>
                  <span className="text-white font-medium text-xs">{systemInfo.uptime_hours} hrs</span>
                </div>
              </div>
            </div>
          </div>

          {/* Hardware Load */}
          <div className="glass-panel p-5 flex flex-col justify-between">
            <div className="flex items-center gap-2 text-white/50 mb-3">
              <HardDrive size={16} />
              <span className="text-xs font-bold uppercase tracking-wider">Hardware Load</span>
            </div>
            <div className="flex flex-col gap-3">
              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-white/60 text-xs">CPU ({systemInfo.cpu_cores} Cores) - {systemInfo.cpu_model}</span>
                  <span className="text-white text-xs font-medium">{systemInfo.cpu_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
                  <div className={`h-full ${systemInfo.cpu_percent > 80 ? 'bg-red-500' : 'bg-primary'}`} style={{ width: `${systemInfo.cpu_percent}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-white/60 text-xs">RAM ({systemInfo.memory_used_gb} GB / {systemInfo.memory_total_gb} GB)</span>
                  <span className="text-white text-xs font-medium">{systemInfo.memory_used_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
                  <div className={`h-full ${systemInfo.memory_used_percent > 80 ? 'bg-red-500' : 'bg-primary'}`} style={{ width: `${systemInfo.memory_used_percent}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-white/60 text-xs">Disk ({systemInfo.disk_used_gb} GB / {systemInfo.disk_total_gb} GB)</span>
                  <span className="text-white text-xs font-medium">{systemInfo.disk_used_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
                  <div className={`h-full ${systemInfo.disk_used_percent > 80 ? 'bg-red-500' : 'bg-blue-500'}`} style={{ width: `${systemInfo.disk_used_percent}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Accelerators & GPU */}
          <div className="glass-panel p-5 flex flex-col justify-between">
            <div className="flex items-center gap-2 text-white/50 mb-3">
              <Cpu size={16} />
              <span className="text-xs font-bold uppercase tracking-wider">Accelerators & GPU</span>
            </div>
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/5 mb-1">
                <span className="text-white/70 text-[10px] uppercase font-bold tracking-wider">Detected GPU</span>
                <span className="text-white/90 text-xs font-medium">{systemInfo.gpu_model}</span>
              </div>
              <div className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/5">
                <span className="text-white/70 text-xs">Apple Neural Engine</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${systemInfo.apple_silicon ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-white/40'}`}>
                  {systemInfo.apple_silicon ? 'Ready' : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/5">
                <span className="text-white/70 text-xs">PaddleOCR Backend</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${systemInfo.paddle_available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {systemInfo.paddle_available ? 'Ready' : 'Missing'}
                </span>
              </div>
              <div className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/5">
                <span className="text-white/70 text-xs">MLX-VLM Backend</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${systemInfo.mlx_available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {systemInfo.mlx_available ? 'Ready' : 'Missing'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Access & Security */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center gap-3 text-white border-b border-white/10 pb-2">
          <ShieldAlert className="text-primary" />
          <h3 className="text-xl font-bold">Access & Security</h3>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          
          {/* Access Control */}
          <div className="glass-panel p-6 flex flex-col gap-4 h-full">
            <div className="flex items-center gap-3 text-white">
              <Globe className="text-primary shrink-0" />
              <h4 className="text-lg font-bold">Access Control</h4>
            </div>
            <p className="text-white/60 text-sm">Control whether the OCR Console is available publicly or requires authentication.</p>
            
            <div className="flex items-center justify-between gap-4 p-4 bg-white/5 rounded-xl border border-white/10 mt-auto">
              <div className="flex-1">
                <p className="text-white font-medium">Public OCR Console</p>
                <p className="text-white/40 text-xs mt-1">If disabled, users must log in.</p>
              </div>
              <button 
                onClick={handleTogglePublic}
                className={`shrink-0 w-14 h-8 rounded-full transition-all relative ${config.is_ocr_public ? 'bg-primary' : 'bg-white/20'}`}
              >
                <div className={`w-6 h-6 bg-white rounded-full absolute top-1 transition-all ${config.is_ocr_public ? 'left-7' : 'left-1'}`} />
              </button>
            </div>
          </div>

          {/* Change Password */}
          <div className="glass-panel p-6 flex flex-col gap-4 h-full">
            <div className="flex items-center gap-3 text-white">
              <Lock className="text-primary shrink-0" />
              <h4 className="text-lg font-bold">Admin Password</h4>
            </div>
            <p className="text-white/60 text-sm">Change the master password used to access settings and private OCR.</p>
            
            <form onSubmit={handleChangePassword} className="flex gap-2 mt-auto w-full">
              <input 
                type="password" 
                placeholder="New Password" 
                className="glass-input flex-1 min-w-0"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                required
              />
              <button type="submit" className="glass-button-primary whitespace-nowrap shrink-0">Update</button>
            </form>
          </div>

          {/* 2FA Setup */}
          <div className="glass-panel p-6 flex flex-col gap-4 h-full">
            <div className="flex items-center gap-3 text-white">
              <QrCode className="text-primary shrink-0" />
              <h4 className="text-lg font-bold">Two-Factor Auth</h4>
            </div>
            
            {!config.is_2fa_enabled && !setup2fa && (
              <>
                <p className="text-white/60 text-sm">Enhance security by requiring an authenticator code.</p>
                <form onSubmit={handleInit2FA} className="flex flex-col gap-3 mt-auto">
                  <input 
                    type="password" 
                    placeholder="Current Password" 
                    className="glass-input w-full"
                    value={passwordFor2fa}
                    onChange={e => setPasswordFor2fa(e.target.value)}
                    required
                  />
                  <button type="submit" className="glass-button-primary flex items-center justify-center gap-2 w-full">
                    Enable 2FA
                  </button>
                </form>
              </>
            )}

            {config.is_2fa_enabled && (
              <div className="flex flex-col h-full justify-center items-center p-4 bg-green-500/5 rounded-xl border border-green-500/20">
                <ShieldAlert className="text-green-400 mb-2" size={32} />
                <p className="text-white font-medium">2FA is Enabled</p>
                <p className="text-white/40 text-xs mt-1 text-center">Your account is secured with TOTP.</p>
              </div>
            )}

            {setup2fa && (
              <div className="flex flex-col gap-4 mt-auto">
                <div className="bg-white p-2 rounded-xl mx-auto w-fit">
                  <QRCodeSVG value={setup2fa.uri} size={100} />
                </div>
                <form onSubmit={handleVerify2FA} className="flex gap-2">
                  <input 
                    type="text" 
                    placeholder="6-digit code" 
                    className="glass-input flex-1 min-w-0 text-center tracking-widest"
                    value={verifyCode}
                    onChange={e => setVerifyCode(e.target.value)}
                    required
                  />
                  <button type="submit" className="glass-button-primary shrink-0">Verify</button>
                </form>
              </div>
            )}
          </div>

        </div>
      </section>

      {/* Section 3: API Keys */}
      <section className="flex flex-col gap-4 pb-10">
        <div className="flex items-center gap-3 text-white border-b border-white/10 pb-2">
          <Key className="text-primary" />
          <h3 className="text-xl font-bold">API Keys</h3>
        </div>
        
        <div className="glass-panel p-6 flex flex-col gap-4">
          <p className="text-white/60 text-sm">Generate secure API keys for programmatic access. Keys are linked to the admin account.</p>
          
          <form onSubmit={handleCreateApiKey} className="flex gap-2 max-w-md">
            <input 
              type="text" 
              placeholder="Key Name (e.g. n8n automation)" 
              className="glass-input flex-1"
              value={newKeyName}
              onChange={e => setNewKeyName(e.target.value)}
              required
            />
            <button type="submit" className="glass-button-primary">Generate</button>
          </form>

          <div className="flex flex-col gap-2 mt-2">
            {apiKeys.map(key => (
              <div key={key.id} className="flex items-center justify-between p-4 bg-black/30 rounded-xl border border-white/10 max-w-2xl">
                <div>
                  <p className="text-white font-medium">{key.name}</p>
                  <p className="text-white/40 text-xs font-mono mt-1">{key.prefix} • Created {new Date(key.created_at).toLocaleDateString()}</p>
                </div>
                <button 
                  onClick={() => handleDeleteApiKey(key.id)}
                  className="px-3 py-1.5 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors border border-transparent hover:border-red-500/30 flex items-center gap-2 text-sm font-medium"
                >
                  <Trash2 size={16} /> Revoke
                </button>
              </div>
            ))}
            {apiKeys.length === 0 && <p className="text-white/30 text-sm py-4">No API keys created yet.</p>}
          </div>
        </div>
      </section>

    </div>
  );
}
