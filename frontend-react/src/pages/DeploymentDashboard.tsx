import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
    AlertCircle, CheckCircle, Pause, Play,
    Trash2, RefreshCw
} from 'lucide-react';

interface Deployment {
    id: string;
    agent_id: string;
    agent_name: string;
    deployment_type: string;
    status: string;
    adapter_used: string;
    environment_name: string;
    deployed_at: string;
    last_health_check: string | null;
    total_invocations: number;
}

interface Stats {
    total_deployments: number;
    active: number;
    stopped: number;
    error: number;
    total_invocations: number;
}

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
    active: { color: 'bg-green-100 text-green-700', icon: <CheckCircle className="w-4 h-4" /> },
    pending: { color: 'bg-yellow-100 text-yellow-700', icon: <RefreshCw className="w-4 h-4 animate-spin" /> },
    stopped: { color: 'bg-gray-100 text-gray-700', icon: <Pause className="w-4 h-4" /> },
    error: { color: 'bg-red-100 text-red-700', icon: <AlertCircle className="w-4 h-4" /> },
    updating: { color: 'bg-blue-100 text-blue-700', icon: <RefreshCw className="w-4 h-4" /> },
};

export function DeploymentDashboard() {
    const { user } = useAuth();
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('');

    useEffect(() => {
        if (user?.id) {
            fetchDeployments();
            fetchStats();
        }
    }, [user?.id, statusFilter]);

    const fetchDeployments = async () => {
        try {
            const params = new URLSearchParams({ user_id: user!.id });
            if (statusFilter) params.append('status', statusFilter);

            const response = await fetch(`/api/v1/deployments?${params}`);
            const data = await response.json();
            setDeployments(data);
        } catch (error) {
            console.error('Failed to fetch deployments:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await fetch(`/api/v1/deployments/stats/summary?user_id=${user!.id}`);
            const data = await response.json();
            setStats(data);
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    };

    const updateStatus = async (deploymentId: string, status: string) => {
        try {
            await fetch(`/api/v1/deployments/${deploymentId}/status?user_id=${user!.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            fetchDeployments();
            fetchStats();
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    };

    const deleteDeployment = async (deploymentId: string) => {
        if (!confirm('Are you sure you want to delete this deployment?')) return;

        try {
            await fetch(`/api/v1/deployments/${deploymentId}?user_id=${user!.id}`, {
                method: 'DELETE'
            });
            fetchDeployments();
            fetchStats();
        } catch (error) {
            console.error('Failed to delete deployment:', error);
        }
    };

    const StatusBadge = ({ status }: { status: string }) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
        return (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
                {config.icon}
                {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
        );
    };

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Deployments</h1>
                    <p className="text-gray-500 mt-1">Monitor your deployed agents</p>
                </div>
                <button
                    onClick={fetchDeployments}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-5 gap-4 mb-8">
                    <div className="bg-white rounded-xl p-5 border border-gray-200">
                        <div className="text-2xl font-bold text-gray-900">{stats.total_deployments}</div>
                        <div className="text-sm text-gray-500">Total Deployments</div>
                    </div>
                    <div className="bg-white rounded-xl p-5 border border-gray-200">
                        <div className="text-2xl font-bold text-green-600">{stats.active}</div>
                        <div className="text-sm text-gray-500">Active</div>
                    </div>
                    <div className="bg-white rounded-xl p-5 border border-gray-200">
                        <div className="text-2xl font-bold text-gray-600">{stats.stopped}</div>
                        <div className="text-sm text-gray-500">Stopped</div>
                    </div>
                    <div className="bg-white rounded-xl p-5 border border-gray-200">
                        <div className="text-2xl font-bold text-red-600">{stats.error}</div>
                        <div className="text-sm text-gray-500">Error</div>
                    </div>
                    <div className="bg-white rounded-xl p-5 border border-gray-200">
                        <div className="text-2xl font-bold text-blue-600">{stats.total_invocations.toLocaleString()}</div>
                        <div className="text-sm text-gray-500">Total Invocations</div>
                    </div>
                </div>
            )}

            {/* Filter */}
            <div className="mb-6">
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                >
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="pending">Pending</option>
                    <option value="stopped">Stopped</option>
                    <option value="error">Error</option>
                </select>
            </div>

            {/* Deployments Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Agent</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Adapter</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Invocations</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {loading ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                                    Loading...
                                </td>
                            </tr>
                        ) : deployments.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                                    No deployments found. Install an agent from the marketplace to get started.
                                </td>
                            </tr>
                        ) : (
                            deployments.map(deployment => (
                                <tr key={deployment.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-gray-900">{deployment.agent_name}</div>
                                        <div className="text-xs text-gray-500">{deployment.environment_name || 'Default'}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="bg-purple-50 text-purple-700 text-xs px-2 py-1 rounded">
                                            {deployment.deployment_type.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-600">{deployment.adapter_used || 'N/A'}</td>
                                    <td className="px-6 py-4">
                                        <StatusBadge status={deployment.status} />
                                    </td>
                                    <td className="px-6 py-4 text-gray-600">
                                        {deployment.total_invocations.toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-2">
                                            {deployment.status === 'active' ? (
                                                <button
                                                    onClick={() => updateStatus(deployment.id, 'stopped')}
                                                    className="p-2 text-gray-500 hover:text-yellow-600 hover:bg-yellow-50 rounded"
                                                    title="Stop"
                                                >
                                                    <Pause className="w-4 h-4" />
                                                </button>
                                            ) : deployment.status === 'stopped' ? (
                                                <button
                                                    onClick={() => updateStatus(deployment.id, 'active')}
                                                    className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded"
                                                    title="Start"
                                                >
                                                    <Play className="w-4 h-4" />
                                                </button>
                                            ) : null}
                                            <button
                                                onClick={() => deleteDeployment(deployment.id)}
                                                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
