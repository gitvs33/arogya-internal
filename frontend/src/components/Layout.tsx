import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Building2, BarChart3, LogOut, LayoutDashboard } from 'lucide-react';
import { getStoredUser, clearStoredUser } from '../api/client';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = getStoredUser();

  const navItems = [
    { path: '/', label: 'Hospitals', icon: Building2 },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/stats', label: 'Platform Stats', icon: BarChart3 },
  ];

  const handleLogout = () => {
    clearStoredUser();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1D4B42] text-white flex flex-col">
        <div className="p-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Arogya OS" className="w-8 h-8 object-contain" />
            <div>
              <h1 className="text-xl leading-tight flex items-baseline gap-1">
                <span className="font-['Playfair_Display'] font-bold">Arogya</span>
                <span className="font-['Inter'] font-bold text-[#CD7526]">OS</span>
              </h1>
              <p className="text-xs text-white/60 font-['Inter']">Operations Panel</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active
                    ? 'bg-white/15 text-white font-medium'
                    : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10">
          <div className="mb-3 px-1">
            <p className="text-sm font-medium truncate">{user?.user?.username || 'Staff'}</p>
            <p className="text-xs text-white/50 truncate">{user?.user?.email || ''}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
