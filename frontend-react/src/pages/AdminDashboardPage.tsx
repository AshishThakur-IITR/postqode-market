import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
    Users, Building, DollarSign, Activity, CheckCircle, XCircle,
    Clock, Shield, Search, Filter, Briefcase
} from 'lucide-react';

interface Stats {
    total_users: number;
    total_agents: number;
    active_licenses: number;
    total_revenue: number;
    monthly_revenue: number;
}

interface PendingOrg {
    id: string;
    name: string;
    slug: string;
    subscription_plan: string;
    created_at: string;
    owner_email?: string; // May need to fetch owner details separately or include in API
}

export function AdminDashboardPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<'overview' | 'orgs' | 'users'>('overview');
    const [stats, setStats] = useState<Stats | null>(null);
    const [pendingOrgs, setPendingOrgs] = useState<PendingOrg[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchStats();
            fetchPendingOrgs();
        }
    }, [user]);

    const fetchStats = async () => {
        try {
            const res = await fetch(`/api/v1/admin/stats?admin_id=${user?.id}`);
            const data = await res.json();
            setStats(data.stats); // Assuming structure matches
        } catch (err) {
            console.error(err);
        }
    };

    const fetchPendingOrgs = async () => {
        try {
            const res = await fetch(`/api/v1/admin/organizations/pending?admin_id=${user?.id}`);
            const data = await res.json();
            setPendingOrgs(data);
        } catch (err) {
            console.error(err);
        }
    };

    const handleApproveOrg = async (orgId: string) => {
        try {
            const res = await fetch(`/api/v1/admin/organizations/${orgId}/approve?admin_id=${user?.id}`, {
                method: 'POST'
            });
            if (res.ok) {
                // Remove from list
                setPendingOrgs(prev => prev.filter(o => o.id !== orgId));
                // Optional: Show success toast
            }
        } catch (err) {
            console.error(err);
        }
    };

    if (isLoading && !stats && !pendingOrgs.length) {
        // Quick loading simulation
        setTimeout(() => setIsLoading(false), 1000);
        return (
            <div className="flex items-center justify-center p-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
                <p className="text-gray-500 mt-1">Platform overview and management</p>
            </div>

            {/* Stats Overview */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-blue-100 rounded-lg">
                                <Users className="w-6 h-6 text-blue-600" />
                            </div>
                            <div>
                                <div className="text-2xl font-bold">{stats.total_users}</div>
                                <div className="text-sm text-gray-500">Total Users</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-purple-100 rounded-lg">
                                <Briefcase className="w-6 h-6 text-purple-600" />
                            </div>
                            <div>
                                <div className="text-2xl font-bold">{stats.total_agents}</div>
                                <div className="text-sm text-gray-500">Total Agents</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-green-100 rounded-lg">
                                <DollarSign className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                                <div className="text-2xl font-bold">${(stats.monthly_revenue / 100).toFixed(0)}</div>
                                <div className="text-sm text-gray-500">Monthly Revenue</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-orange-100 rounded-lg">
                                <Activity className="w-6 h-6 text-orange-600" />
                            </div>
                            <div>
                                <div className="text-2xl font-bold">{stats.active_licenses}</div>
                                <div className="text-sm text-gray-500">Active Licenses</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-gray-200 mb-6">
                <button
                    onClick={() => setActiveTab('overview')}
                    className={`px-6 py-3 font-medium text-sm transition-colors relative ${activeTab === 'overview' ? 'text-green-600' : 'text-gray-500 hover:text-gray-700'
                        }`}
                >
                    Overview
                    {activeTab === 'overview' && (
                        <div className="absolute bottom-0 left-0 w-full h-0.5 bg-green-600" />
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('orgs')}
                    className={`px-6 py-3 font-medium text-sm transition-colors relative ${activeTab === 'orgs' ? 'text-green-600' : 'text-gray-500 hover:text-gray-700'
                        }`}
                >
                    Organizations
                    {pendingOrgs.length > 0 && (
                        <span className="ml-2 bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full">
                            {pendingOrgs.length}
                        </span>
                    )}
                    {activeTab === 'orgs' && (
                        <div className="absolute bottom-0 left-0 w-full h-0.5 bg-green-600" />
                    )}
                </button>
            </div>

            {/* Content */}
            {activeTab === 'orgs' && (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                        <h2 className="text-lg font-semibold">Pending Approvals</h2>
                    </div>
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Organization</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Plan</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Requested</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {pendingOrgs.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                                        No organizations pending approval.
                                    </td>
                                </tr>
                            ) : (
                                pendingOrgs.map(org => (
                                    <tr key={org.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-gray-900">{org.name}</div>
                                            <div className="text-sm text-gray-500">{org.slug}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                {org.subscription_plan}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-500">
                                            {new Date(org.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handleApproveOrg(org.id)}
                                                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors flex items-center gap-1"
                                            >
                                                <CheckCircle className="w-4 h-4" />
                                                Approve
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {activeTab === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <button onClick={() => navigate('/admin/users')} className="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left">
                                <Users className="w-6 h-6 text-green-600 mb-2" />
                                <div className="font-medium">Manage Users</div>
                                <div className="text-xs text-gray-500">View and edit user roles</div>
                            </button>
                            <button onClick={() => navigate('/admin/agents')} className="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left">
                                <Shield className="w-6 h-6 text-green-600 mb-2" />
                                <div className="font-medium">Review Agents</div>
                                <div className="text-xs text-gray-500">Approve pending agents</div>
                            </button>
                            <button onClick={() => navigate('/admin/licenses')} className="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left">
                                <Activity className="w-6 h-6 text-green-600 mb-2" />
                                <div className="font-medium">Licenses</div>
                                <div className="text-xs text-gray-500">Monitor active licenses</div>
                            </button>
                            <button onClick={() => setActiveTab('orgs')} className="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left">
                                <Building className="w-6 h-6 text-green-600 mb-2" />
                                <div className="font-medium">Organizations</div>
                                <div className="text-xs text-gray-500">Approve new organizations</div>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
