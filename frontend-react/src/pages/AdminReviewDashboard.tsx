import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
    CheckCircle, XCircle, Clock, Eye, Archive,
    AlertTriangle, Users, Package
} from 'lucide-react';

interface AgentData {
    id: string;
    name: string;
    description: string;
    category: string;
    price_cents: number;
    status: string;
    version: string;
    submitted_at?: string;
    publisher_id: string;
}

interface AdminStats {
    total_agents: number;
    pending_review: number;
    published: number;
    drafts: number;
    rejected: number;
    archived: number;
    total_publishers: number;
}

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
    draft: { color: 'bg-gray-100 text-gray-700', label: 'Draft' },
    pending_review: { color: 'bg-yellow-100 text-yellow-700', label: 'Pending Review' },
    published: { color: 'bg-green-100 text-green-700', label: 'Published' },
    rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected' },
    archived: { color: 'bg-slate-100 text-slate-700', label: 'Archived' },
};

export function AdminReviewDashboard() {
    const { user } = useAuth();
    const [agents, setAgents] = useState<AgentData[]>([]);
    const [stats, setStats] = useState<AdminStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [statusFilter, setStatusFilter] = useState('pending_review');
    const [selectedAgent, setSelectedAgent] = useState<AgentData | null>(null);
    const [rejectReason, setRejectReason] = useState('');
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        if (user?.id) {
            fetchStats();
            fetchAgents();
        }
    }, [user?.id, statusFilter]);

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/v1/admin/stats?admin_id=' + user!.id);
            if (response.status === 403) {
                setError('Admin privileges required');
                return;
            }
            const data = await response.json();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    };

    const fetchAgents = async () => {
        try {
            const url = statusFilter === 'pending_review'
                ? '/api/v1/admin/agents/pending?admin_id=' + user!.id
                : '/api/v1/admin/agents/all?admin_id=' + user!.id + '&status_filter=' + statusFilter;

            const response = await fetch(url);
            if (!response.ok) {
                if (response.status === 403) {
                    setError('Admin privileges required');
                    return;
                }
                throw new Error('Failed to fetch');
            }
            const data = await response.json();
            setAgents(data);
        } catch (err) {
            console.error('Failed to fetch agents:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (agentId: string) => {
        setActionLoading(true);
        try {
            const response = await fetch(
                '/api/v1/admin/agents/' + agentId + '/approve?admin_id=' + user!.id,
                { method: 'POST' }
            );
            if (!response.ok) throw new Error('Failed to approve');
            fetchAgents();
            fetchStats();
        } catch (err) {
            console.error('Failed to approve:', err);
        } finally {
            setActionLoading(false);
        }
    };

    const handleReject = async () => {
        if (!selectedAgent || !rejectReason) return;
        setActionLoading(true);
        try {
            const response = await fetch(
                '/api/v1/admin/agents/' + selectedAgent.id + '/reject?admin_id=' + user!.id,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason: rejectReason })
                }
            );
            if (!response.ok) throw new Error('Failed to reject');
            setShowRejectModal(false);
            setRejectReason('');
            setSelectedAgent(null);
            fetchAgents();
            fetchStats();
        } catch (err) {
            console.error('Failed to reject:', err);
        } finally {
            setActionLoading(false);
        }
    };

    const handleArchive = async (agentId: string) => {
        setActionLoading(true);
        try {
            const response = await fetch(
                '/api/v1/admin/agents/' + agentId + '/archive?admin_id=' + user!.id,
                { method: 'POST' }
            );
            if (!response.ok) throw new Error('Failed to archive');
            fetchAgents();
            fetchStats();
        } catch (err) {
            console.error('Failed to archive:', err);
        } finally {
            setActionLoading(false);
        }
    };

    const StatusBadge = ({ status }: { status: string }) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
        return (
            <span className={'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ' + config.color}>
                {config.label}
            </span>
        );
    };

    if (error) {
        return (
            <div className="fixed inset-0 z-[100] bg-white flex items-center justify-center p-4">
                <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-xl p-8 text-center shadow-lg">
                    <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-6" />
                    <h2 className="text-2xl font-bold text-red-700 mb-3">Access Denied</h2>
                    <p className="text-red-600 text-lg mb-6">{error}</p>
                    <div className="bg-white rounded-lg p-4 border border-red-100">
                        <p className="text-sm text-gray-500 mb-2">
                            This area is restricted to Super Admins only.
                        </p>
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded block mb-4">
                            superadmin@postqode.io
                        </code>
                        <a
                            href="/login"
                            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                            Log in as Super Admin
                        </a>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Admin Review Dashboard</h1>
                <p className="text-gray-500 mt-1">Review and approve agent submissions</p>
            </div>

            {stats && (
                <div className="grid grid-cols-4 gap-4 mb-8">
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-yellow-100 rounded-lg">
                                <Clock className="w-6 h-6 text-yellow-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.pending_review}</div>
                                <div className="text-sm text-gray-500">Pending Review</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-green-100 rounded-lg">
                                <CheckCircle className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.published}</div>
                                <div className="text-sm text-gray-500">Published</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-blue-100 rounded-lg">
                                <Package className="w-6 h-6 text-blue-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.total_agents}</div>
                                <div className="text-sm text-gray-500">Total Agents</div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-purple-100 rounded-lg">
                                <Users className="w-6 h-6 text-purple-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.total_publishers}</div>
                                <div className="text-sm text-gray-500">Publishers</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="mb-6 flex gap-2">
                {['pending_review', 'published', 'rejected', 'draft', 'archived'].map(status => (
                    <button
                        key={status}
                        onClick={() => setStatusFilter(status)}
                        className={'px-4 py-2 rounded-lg text-sm font-medium transition-colors ' +
                            (statusFilter === status
                                ? 'bg-green-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            )}
                    >
                        {STATUS_CONFIG[status]?.label || status}
                    </button>
                ))}
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Agent</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Price</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Submitted</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {loading ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">Loading...</td>
                            </tr>
                        ) : agents.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                                    No agents found with status "{STATUS_CONFIG[statusFilter]?.label || statusFilter}"
                                </td>
                            </tr>
                        ) : (
                            agents.map(agent => (
                                <tr key={agent.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-gray-900">{agent.name}</div>
                                        <div className="text-sm text-gray-500 truncate max-w-xs">{agent.description}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="bg-green-50 text-green-700 text-xs px-2 py-1 rounded-full">
                                            {agent.category}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-900 font-medium">
                                        ${(agent.price_cents / 100).toFixed(2)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <StatusBadge status={agent.status} />
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-500">
                                        {agent.submitted_at ? new Date(agent.submitted_at).toLocaleDateString() : '-'}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-2">
                                            {agent.status === 'pending_review' && (
                                                <>
                                                    <button
                                                        onClick={() => handleApprove(agent.id)}
                                                        disabled={actionLoading}
                                                        className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200 disabled:opacity-50"
                                                    >
                                                        <CheckCircle className="w-3 h-3" />
                                                        Approve
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setSelectedAgent(agent);
                                                            setShowRejectModal(true);
                                                        }}
                                                        className="flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200"
                                                    >
                                                        <XCircle className="w-3 h-3" />
                                                        Reject
                                                    </button>
                                                </>
                                            )}
                                            {agent.status === 'published' && (
                                                <button
                                                    onClick={() => handleArchive(agent.id)}
                                                    disabled={actionLoading}
                                                    className="flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
                                                >
                                                    <Archive className="w-3 h-3" />
                                                    Archive
                                                </button>
                                            )}
                                            <button
                                                onClick={() => setSelectedAgent(agent)}
                                                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                                                title="View Details"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {showRejectModal && selectedAgent && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-md">
                        <h2 className="text-xl font-bold mb-4">Reject Agent</h2>
                        <p className="text-gray-600 mb-4">
                            Rejecting <strong>{selectedAgent.name}</strong>. Please provide a reason:
                        </p>
                        <textarea
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            rows={4}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                            placeholder="Enter rejection reason..."
                        />
                        <div className="flex justify-end gap-3 mt-4">
                            <button
                                onClick={() => {
                                    setShowRejectModal(false);
                                    setRejectReason('');
                                    setSelectedAgent(null);
                                }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleReject}
                                disabled={!rejectReason || actionLoading}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Rejecting...' : 'Reject Agent'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {selectedAgent && !showRejectModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-lg">
                        <div className="flex justify-between items-start mb-4">
                            <h2 className="text-xl font-bold">{selectedAgent.name}</h2>
                            <StatusBadge status={selectedAgent.status} />
                        </div>
                        <div className="space-y-4 text-sm">
                            <div>
                                <span className="font-medium text-gray-500">Description:</span>
                                <p className="text-gray-900 mt-1">{selectedAgent.description}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <span className="font-medium text-gray-500">Category:</span>
                                    <p className="text-gray-900">{selectedAgent.category}</p>
                                </div>
                                <div>
                                    <span className="font-medium text-gray-500">Price:</span>
                                    <p className="text-gray-900">${(selectedAgent.price_cents / 100).toFixed(2)}</p>
                                </div>
                                <div>
                                    <span className="font-medium text-gray-500">Version:</span>
                                    <p className="text-gray-900">{selectedAgent.version}</p>
                                </div>
                                <div>
                                    <span className="font-medium text-gray-500">Agent ID:</span>
                                    <p className="text-gray-900 text-xs font-mono">{selectedAgent.id}</p>
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end mt-6">
                            <button
                                onClick={() => setSelectedAgent(null)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
