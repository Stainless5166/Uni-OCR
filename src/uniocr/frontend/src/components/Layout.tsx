import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { ScanText, Settings, FileCode2, LogOut } from 'lucide-react';

export default function Layout() {
  const navigate = useNavigate();
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="flex h-screen w-full relative z-10 p-4 gap-4">
      {/* Sidebar */}
      <aside className="w-20 md:w-64 glass-panel flex flex-col justify-between py-6 transition-all">
        <div className="flex flex-col items-center md:items-stretch px-4 gap-8">
          <div className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-purple-500 flex items-center justify-center shadow-lg">
              <ScanText className="text-white" size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight hidden md:block bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
              UniOCR
            </h1>
          </div>
          
          <nav className="flex flex-col gap-2">
            <NavLink to="/" className={({isActive}) => `flex items-center gap-3 px-3 py-3 rounded-xl transition-all ${isActive ? 'bg-white/10 text-white shadow-inner' : 'text-white/50 hover:bg-white/5 hover:text-white'}`}>
              <ScanText size={20} />
              <span className="hidden md:block font-medium">Console</span>
            </NavLink>
            <NavLink to="/docs-ui" className={({isActive}) => `flex items-center gap-3 px-3 py-3 rounded-xl transition-all ${isActive ? 'bg-white/10 text-white shadow-inner' : 'text-white/50 hover:bg-white/5 hover:text-white'}`}>
              <FileCode2 size={20} />
              <span className="hidden md:block font-medium">API Docs</span>
            </NavLink>
            <NavLink to="/settings" className={({isActive}) => `flex items-center gap-3 px-3 py-3 rounded-xl transition-all ${isActive ? 'bg-white/10 text-white shadow-inner' : 'text-white/50 hover:bg-white/5 hover:text-white'}`}>
              <Settings size={20} />
              <span className="hidden md:block font-medium">Settings</span>
            </NavLink>
          </nav>
        </div>
        
        <div className="px-4">
          <button onClick={handleLogout} className="w-full flex items-center justify-center md:justify-start gap-3 px-3 py-3 rounded-xl text-red-400 hover:bg-red-500/10 transition-all">
            <LogOut size={20} />
            <span className="hidden md:block font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 glass-panel overflow-hidden relative">
        <div className="absolute inset-0 overflow-y-auto custom-scrollbar">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
