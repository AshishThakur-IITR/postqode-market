import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Filter, Search, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface License {
    id: string;
    user_name: string;
    user_email: string;
    agent_name: string;
    agent_id: string;
    status: string;
    start_date: string;
    end_date: string;
    price_cents: number;
}

export function LicenseManagementPage() {
    const { user } = useAuth();
    const [licenses, setLicenses] = useState<License[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    useEffect(() => {
        if (user?.id) {
            fetchLicenses();
        }
    }, [user?.id, statusFilter]);

    const fetchLicenses = async () => {
        try {
            const url = statusFilter === 'all'
                ? '/api/v1/admin/licenses?admin_id=' + user?.id
                : `/api/v1/admin/licenses?admin_id=${user?.id}&status_filter=${statusFilter}`;
            const response = await fetch(url);
            const data = await response.json();
            setLicenses(data);
        } catch (error) {
            console.error('Failed to fetch licenses:', error);
        } finally {
            setLoading(false);
        }
    };

    const updateLicenseStatus = async (licenseId: string, newStatus: string) => {
        setActionLoading(licenseId);
        try {
            const response = await fetch(
                `/api/v1/admin/licenses/${licenseId}/status?admin_id=${user?.id}&new_status=${newStatus}`,
                { method: 'PUT' }
            );
            if (response.ok) {
                await fetchLicenses();
            }
        } catch (error) {
            console.error('Failed to update license:', error);
        } finally {
            setActionLoading(null);
        }
    };

    const filteredLicenses = licenses.filter(lic =>
        lic.user_name.toLowerCase().includes(search.toLowerCase()) ||
        lic.user_email.toLowerCase().includes(search.toLowerCase()) ||
        lic.agent_name.toLowerCase().includes(search.toLowerCase())
    );

    const getStatusBadge = (status: string) => {
        const statusLower = status.toLowerCase();
        if (statusLower === 'active') {
            return <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium"><CheckCircle className="w-3 h-3" />Active</span>;
        }
        if (statusLower === 'suspended') {
            return <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium"><XCircle className="w-3 h-3" />Suspended</span>;
        }
        return <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium"><AlertCircle className="w-3 h-3" />{status}</span>;
    };

    if (loading) {
        return <div className="p-8 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent" /></div>;
    }

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">License Management</h1>
                <p className="text-gray-500 mt-1">View and manage all marketplace licenses</p>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl p-6 border border-gray-200 mb-6">
                <div className="flex gap-4">
                    <div className="flex-1">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                            <input
                                type="text"
                                placeholder="Search by user, email, or agent..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            />
                        </div>
                    </div>
                    <div className="relative min-w-[200px]">
                        <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 appearance-none"
                        >
                            <option value="all">All Status</option>
                            <option value="active">Active</option>
                            <option value="suspended">Suspended</option>
                            <option value="expired">Expired</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Licenses Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">User</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Agent</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Start Date</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">End Date</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Revenue</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {filteredLicenses.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                    {search || statusFilter !== 'all' ? 'No licenses match your filters.' : 'No licenses found.'}
                                </td>
                            </tr>
                        ) : (
                            filteredLicenses.map(lic => (
                                <tr key={lic.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-gray-900">{lic.user_name}</div>
                                        <div className="text-sm text-gray-500">{lic.user_email}</div>
                                    </td>
                                    <td className="px-6 py-4 font-medium text-gray-900">{lic.agent_name}</td>
                                    <td className="px-6 py-4">{getStatusBadge(lic.status)}</td>
                                    <td className="px-6 py-4 text-sm text-gray-600">
                                        {new Date(lic.start_date).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-600">
                                        {new Date(lic.end_date).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 font-medium text-gray-900">
                                        ${(lic.price_cents / 100).toFixed(2)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-2">
                                            {lic.status.toLowerCase() === 'active' ? (
                                                <button
                                                    onClick={() => updateLicenseStatus(lic.id, 'SUSPENDED')}
                                                    disabled={actionLoading === lic.id}
                                                    className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                                                >
                                                    {actionLoading === lic.id ? 'Processing...' : 'Suspend'}
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => updateLicenseStatus(lic.id, 'ACTIVE')}
                                                    disabled={actionLoading === lic.id}
                                                    className="text-sm text-green-600 hover:text-green-700 font-medium disabled:opacity-50"
                                                >
                                                    {actionLoading === lic.id ? 'Processing...' : 'Reactivate'}
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Summary */}
            {filteredLicenses.length > 0 && (
                <div className="mt-4 text-sm text-gray-500 text-center">
                    Showing {filteredLicenses.length} of {licenses.length} license{licenses.length !== 1 ? 's' : ''}
                </div>
            )}
        </div>
    );
}
