import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    Store, LayoutDashboard, FileText, Shield, Users,
    Home, HelpCircle, MessageCircle, LogOut
} from 'lucide-react';

export function Sidebar() {
    const location = useLocation();
    const { user, logout } = useAuth();

    const isActive = (path: string) => location.pathname === path;

    const navItem = (path: string, icon: React.ReactNode, label: string) => (
        <Link
            to={path}
            className={`flex items-center gap-3 px-4 py-2 my-0.5 text-sm font-medium rounded-lg transition-colors ${isActive(path)
                ? 'text-gray-900 bg-gray-100' // Darker text for active state
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
        >
            <span className={isActive(path) ? 'text-gray-800' : 'text-gray-500'}>
                {icon}
            </span>
            {label}
        </Link>
    );

    const sectionHeader = (title: string) => (
        <div className="pt-6 pb-2 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">
            {title}
        </div>
    );

    return (
        <div className="w-[220px] h-screen bg-white border-r border-gray-200 fixed left-0 top-0 flex flex-col z-50">
            {/* Logo */}
            <div className="p-6">
                <img
                    src="/src/assets/PostQode.jpg"
                    alt="PostQode"
                    className="h-10 w-10 rounded-lg bg-emerald-500" // Placeholder styling if image fails
                />
            </div>

            {/* Navigation */}
            <div className="flex-1 overflow-y-auto px-3 pb-4">
                {/* HEADERS are bold gray uppercase, items have icons */}

                {sectionHeader('MAIN')}
                {navItem('/', <Home className="w-5 h-5" />, 'Home')}
                {navItem('/contact', <HelpCircle className="w-5 h-5" />, 'Contact Us')}
                {navItem('/faq', <MessageCircle className="w-5 h-5" />, 'FAQ')}

                {sectionHeader('BUYER')}
                {navItem('/marketplace', <Store className="w-5 h-5" />, 'Marketplace')}
                {navItem('/dashboard', <LayoutDashboard className="w-5 h-5" />, 'Dashboard')}
                {navItem('/deployments', <LayoutDashboard className="w-5 h-5" />, 'My Deployments')}


                {sectionHeader('PUBLISHER')}
                {navItem('/publisher/new', <FileText className="w-5 h-5" />, 'Publish New Agent')}
                {navItem('/publisher', <LayoutDashboard className="w-5 h-5" />, 'My Agents')}
                {navItem('/subscribers', <Users className="w-5 h-5" />, 'Subscribers')}

                {sectionHeader('ADMIN')}
                {navItem('/admin', <LayoutDashboard className="w-5 h-5" />, 'Dashboard')}
                {navItem('/admin/users', <Users className="w-5 h-5" />, 'User Roles')}
                {/* Specific active state styling for Agent Review based on screenshot */}
                <Link
                    to="/admin/agents"
                    className={`flex items-center gap-3 px-4 py-2 my-0.5 text-sm font-medium rounded-lg transition-colors ${isActive('/admin/agents')
                        ? 'text-green-800 bg-green-50 font-semibold'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                        }`}
                >
                    <FileText className={`w-5 h-5 ${isActive('/admin/agents') ? 'text-green-700' : 'text-gray-500'}`} />
                    Agent Review
                </Link>
                {navItem('/admin/licenses', <Shield className="w-5 h-5" />, 'Licenses')}

            </div>

            {/* User Profile */}
            <div className="p-4 border-t border-gray-100">
                <div className="flex items-center gap-3 p-2 rounded-lg mb-3">
                    <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white font-bold text-sm">
                        {user?.name?.[0]?.toUpperCase() || 'SA'}
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <div className="text-sm font-bold text-gray-900 truncate">{user?.name || 'Super Admin'}</div>
                        <div className="text-xs text-gray-400 truncate tracking-wide">{user?.role || 'SUPER_ADMIN'}</div>
                    </div>
                </div>
                <button
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
