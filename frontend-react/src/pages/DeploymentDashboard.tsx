import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
    AlertCircle, CheckCircle, Pause, Play,
    Trash2, RefreshCw, Settings, ExternalLink, Loader2,
    Box, Container, Cloud, Server, Cpu, Zap
} from 'lucide-react';

interface Deployment {
    id: string;
    agent_id: string;
    agent_name: string | null;
    deployment_type: string;
    status: string;
    adapter_used?: string | null;
    environment_name?: string | null;
    deployed_at: string;
    last_health_check?: string | null;
    total_invocations?: number;
    deployment_config?: {
        env_vars?: Record<string, string>;
        port?: number;
    };
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
    const [actionLoading, setActionLoading] = useState<string | null>(null);

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

    const handleStart = async (deploymentId: string) => {
        setActionLoading(deploymentId);
        try {
            const response = await fetch(`/api/v1/unified/deploy/${deploymentId}/start?user_id=${user!.id}`, {
                method: 'POST'
            });

            if (response.ok) {
                fetchDeployments();
                fetchStats();
            } else {
                const error = await response.json();
                alert(`Failed to start: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to start deployment:', error);
        } finally {
            setActionLoading(null);
        }
    };

    const handleStop = async (deploymentId: string) => {
        setActionLoading(deploymentId);
        try {
            const response = await fetch(`/api/v1/unified/deploy/${deploymentId}/stop?user_id=${user!.id}`, {
                method: 'POST'
            });

            if (response.ok) {
                fetchDeployments();
                fetchStats();
            } else {
                const error = await response.json();
                alert(`Failed to stop: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to stop deployment:', error);
        } finally {
            setActionLoading(null);
        }
    };

    const deleteDeployment = async (deploymentId: string) => {
        if (!confirm('Are you sure you want to delete this deployment?')) return;

        setActionLoading(deploymentId);
        try {
            await fetch(`/api/v1/deployments/${deploymentId}?user_id=${user!.id}`, {
                method: 'DELETE'
            });
            fetchDeployments();
            fetchStats();
        } catch (error) {
            console.error('Failed to delete deployment:', error);
        } finally {
            setActionLoading(null);
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

    const PLATFORM_CONFIG: Record<string, { icon: React.ReactNode; color: string; name: string }> = {
        docker: { icon: <Box className="w-4 h-4" />, color: 'bg-blue-50 text-blue-700', name: 'Docker' },
        kubernetes: { icon: <Container className="w-4 h-4" />, color: 'bg-purple-50 text-purple-700', name: 'Kubernetes' },
        azure_functions: { icon: <Zap className="w-4 h-4" />, color: 'bg-amber-50 text-amber-700', name: 'Azure Functions' },
        serverless: { icon: <Zap className="w-4 h-4" />, color: 'bg-amber-50 text-amber-700', name: 'Serverless' },
        vm_standalone: { icon: <Server className="w-4 h-4" />, color: 'bg-gray-100 text-gray-700', name: 'VM / Bare Metal' },
        edge: { icon: <Cpu className="w-4 h-4" />, color: 'bg-teal-50 text-teal-700', name: 'Edge Device' },
        cloud_managed: { icon: <Cloud className="w-4 h-4" />, color: 'bg-green-50 text-green-700', name: 'Cloud Managed' },
    };

    const PlatformBadge = ({ platform }: { platform: string }) => {
        const config = PLATFORM_CONFIG[platform] || PLATFORM_CONFIG.docker;
        return (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ${config.color}`}>
                {config.icon}
                {config.name}
            </span>
        );
    };

    const getContainerUrl = (deployment: Deployment): string | null => {
        if (deployment.status !== 'active') return null;
        const port = deployment.deployment_config?.port || 8080;
        return `http://localhost:${port}`;
    };

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Deployments</h1>
                    <p className="text-gray-500 mt-1">Monitor and manage your deployed agents</p>
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
                        <div className="text-2xl font-bold text-blue-600">{(stats.total_invocations ?? 0).toLocaleString()}</div>
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
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">URL</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Invocations</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {loading ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                                    Loading...
                                </td>
                            </tr>
                        ) : deployments.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                    No deployments found. Install an agent from the marketplace to get started.
                                </td>
                            </tr>
                        ) : (
                            deployments.map(deployment => {
                                const containerUrl = getContainerUrl(deployment);
                                const isLoading = actionLoading === deployment.id;

                                return (
                                    <tr key={deployment.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-gray-900">{deployment.agent_name || 'Unknown Agent'}</div>
                                            <div className="text-xs text-gray-500">{deployment.environment_name || 'Default'}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <PlatformBadge platform={deployment.deployment_type || 'docker'} />
                                        </td>
                                        <td className="px-6 py-4 text-gray-600">{deployment.adapter_used || 'N/A'}</td>
                                        <td className="px-6 py-4">
                                            <StatusBadge status={deployment.status} />
                                        </td>
                                        <td className="px-6 py-4">
                                            {containerUrl ? (
                                                <a
                                                    href={containerUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 text-sm text-green-600 hover:text-green-700"
                                                >
                                                    <ExternalLink className="w-3 h-3" />
                                                    {containerUrl}
                                                </a>
                                            ) : (
                                                <span className="text-gray-400 text-sm">-</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-gray-600">
                                            {(deployment.total_invocations ?? 0).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex gap-1">
                                                {isLoading ? (
                                                    <div className="p-2">
                                                        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                                                    </div>
                                                ) : (
                                                    <>
                                                        {deployment.status === 'active' ? (
                                                            <button
                                                                onClick={() => handleStop(deployment.id)}
                                                                className="p-2 text-gray-500 hover:text-yellow-600 hover:bg-yellow-50 rounded"
                                                                title="Stop"
                                                            >
                                                                <Pause className="w-4 h-4" />
                                                            </button>
                                                        ) : deployment.status === 'stopped' || deployment.status === 'error' ? (
                                                            <button
                                                                onClick={() => handleStart(deployment.id)}
                                                                className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded"
                                                                title="Start"
                                                            >
                                                                <Play className="w-4 h-4" />
                                                            </button>
                                                        ) : null}
                                                        <button
                                                            onClick={() => {/* TODO: Open reconfigure modal */ }}
                                                            className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                                                            title="Reconfigure"
                                                        >
                                                            <Settings className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => deleteDeployment(deployment.id)}
                                                            className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                                                            title="Delete"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

