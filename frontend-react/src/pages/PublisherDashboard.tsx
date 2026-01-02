import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Edit, Send, Clock, CheckCircle, XCircle, Archive, Eye } from 'lucide-react';

interface AgentData {
    id: string;
    name: string;
    description: string;
    category: string;
    price_cents: number;
    status: string;
    submitted_at?: string;
    published_at?: string;
    rejection_reason?: string;
    created_at?: string;
}

interface PublisherStats {
    total_agents: number;
    published: number;
    pending_review: number;
    drafts: number;
}

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    draft: { color: 'bg-gray-100 text-gray-700', icon: <Edit className="w-3 h-3" />, label: 'Draft' },
    pending_review: { color: 'bg-yellow-100 text-yellow-700', icon: <Clock className="w-3 h-3" />, label: 'Pending Review' },
    approved: { color: 'bg-blue-100 text-blue-700', icon: <CheckCircle className="w-3 h-3" />, label: 'Approved' },
    published: { color: 'bg-green-100 text-green-700', icon: <CheckCircle className="w-3 h-3" />, label: 'Published' },
    rejected: { color: 'bg-red-100 text-red-700', icon: <XCircle className="w-3 h-3" />, label: 'Rejected' },
    archived: { color: 'bg-slate-100 text-slate-700', icon: <Archive className="w-3 h-3" />, label: 'Archived' },
};

const CATEGORIES = [
    'Data Analytics',
    'Finance',
    'Procurement',
    'Service Operations',
    'Customer Service',
    'Marketing',
    'HR',
    'Other'
];

export function PublisherDashboard() {
    const { user } = useAuth();
    const [agents, setAgents] = useState<AgentData[]>([]);
    const [stats, setStats] = useState<PublisherStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState<AgentData | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('');

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        category: 'Data Analytics',
        price_cents: 0,
        version: '1.0.0'
    });
    const [formError, setFormError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (user?.id) {
            fetchMyAgents();
            fetchStats();
        }
    }, [user?.id, statusFilter]);

    const fetchMyAgents = async () => {
        try {
            const params = new URLSearchParams();
            params.append('publisher_id', user!.id);
            if (statusFilter) params.append('status_filter', statusFilter);

            const response = await fetch(`/api/v1/market/agents/my/list?${params.toString()}`);
            const data = await response.json();
            setAgents(data);
        } catch (error) {
            console.error('Failed to fetch agents:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await fetch(`/api/v1/market/dashboard?user_id=${user!.id}`);
            const data = await response.json();
            setStats(data.publisher_stats);
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    };

    const handleCreateAgent = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setFormError('');

        try {
            const response = await fetch(`/api/v1/market/agents?publisher_id=${user!.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create agent');
            }

            setShowCreateModal(false);
            setFormData({ name: '', description: '', category: 'Data Analytics', price_cents: 0, version: '1.0.0' });
            fetchMyAgents();
            fetchStats();
        } catch (error: any) {
            setFormError(error.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSubmitForReview = async (agentId: string) => {
        try {
            const response = await fetch(`/api/v1/market/agents/${agentId}/submit?publisher_id=${user!.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: '' })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to submit agent');
            }

            fetchMyAgents();
            fetchStats();
        } catch (error) {
            console.error('Failed to submit agent:', error);
        }
    };

    const StatusBadge = ({ status }: { status: string }) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
        return (
            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
                {config.icon}
                {config.label}
            </span>
        );
    };

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Publisher Dashboard</h1>
                    <p className="text-gray-500 mt-1">Manage your agent submissions</p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                >
                    <Plus className="w-5 h-5" />
                    Submit New Agent
                </button>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-4 gap-4 mb-8">
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="text-3xl font-bold text-gray-900">{stats.total_agents}</div>
                        <div className="text-sm text-gray-500 mt-1">Total Agents</div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="text-3xl font-bold text-green-600">{stats.published}</div>
                        <div className="text-sm text-gray-500 mt-1">Published</div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="text-3xl font-bold text-yellow-600">{stats.pending_review}</div>
                        <div className="text-sm text-gray-500 mt-1">Pending Review</div>
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="text-3xl font-bold text-gray-600">{stats.drafts}</div>
                        <div className="text-sm text-gray-500 mt-1">Drafts</div>
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
                    <option value="draft">Drafts</option>
                    <option value="pending_review">Pending Review</option>
                    <option value="published">Published</option>
                    <option value="rejected">Rejected</option>
                    <option value="archived">Archived</option>
                </select>
            </div>

            {/* Agents Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Agent</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Price</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {loading ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                                    Loading...
                                </td>
                            </tr>
                        ) : agents.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                                    No agents found. Click "Submit New Agent" to create one.
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
                                        {agent.rejection_reason && (
                                            <div className="text-xs text-red-600 mt-1">
                                                Reason: {agent.rejection_reason}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setSelectedAgent(agent)}
                                                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                                                title="View Details"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </button>
                                            {(agent.status === 'draft' || agent.status === 'rejected') && (
                                                <button
                                                    onClick={() => handleSubmitForReview(agent.id)}
                                                    className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200"
                                                >
                                                    <Send className="w-3 h-3" />
                                                    Submit
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

            {/* Create Agent Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-lg">
                        <h2 className="text-xl font-bold mb-4">Submit New Agent</h2>
                        <form onSubmit={handleCreateAgent}>
                            {formError && (
                                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                                    {formError}
                                </div>
                            )}
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                    <textarea
                                        required
                                        rows={3}
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                        <select
                                            value={formData.category}
                                            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                        >
                                            {CATEGORIES.map(cat => (
                                                <option key={cat} value={cat}>{cat}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Price (USD)</label>
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            required
                                            value={formData.price_cents / 100 || ''}
                                            onChange={(e) => {
                                                const val = parseFloat(e.target.value);
                                                setFormData({ ...formData, price_cents: isNaN(val) ? 0 : Math.round(val * 100) });
                                            }}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                                    <input
                                        type="text"
                                        value={formData.version}
                                        onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                                >
                                    {isSubmitting ? 'Creating...' : 'Create Draft'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Agent Detail Modal */}
            {selectedAgent && (
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
                            </div>
                            {selectedAgent.rejection_reason && (
                                <div className="p-3 bg-red-50 rounded-lg">
                                    <span className="font-medium text-red-700">Rejection Reason:</span>
                                    <p className="text-red-600 mt-1">{selectedAgent.rejection_reason}</p>
                                </div>
                            )}
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
