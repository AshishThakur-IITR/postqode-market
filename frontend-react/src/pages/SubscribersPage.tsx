import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
    Users, TrendingUp, DollarSign, Filter, Search,
    Calendar, CheckCircle, Eye, Download
} from 'lucide-react';

interface Subscriber {
    id: string;
    user_name: string;
    user_email: string;
    agent_name: string;
    agent_id: string;
    license_status: string;
    start_date: string;
    end_date: string;
    price_cents: number;
}

interface SubscriberStats {
    total_subscribers: number;
    active_licenses: number;
    monthly_revenue: number;
    total_revenue: number;
}

export function SubscribersPage() {
    const { user } = useAuth();
    const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
    const [stats, setStats] = useState<SubscriberStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAgent, setSelectedAgent] = useState<string>('all');
    const [agentList, setAgentList] = useState<any[]>([]);

    useEffect(() => {
        if (user?.id) {
            fetchData();
        }
    }, [user?.id]);

    const fetchData = async () => {
        try {
            const response = await fetch('/api/v1/market/publisher/subscribers?publisher_id=' + user?.id);
            const data = await response.json();
            setSubscribers(data.subscribers || []);
            setStats(data.stats || null);

            // Extract unique agents for filter
            const uniqueAgents = Array.from(new Set(data.subscribers.map((s: Subscriber) => s.agent_name)))
                .map(name => ({
                    id: data.subscribers.find((s: Subscriber) => s.agent_name === name)?.agent_id,
                    name
                }));
            setAgentList(uniqueAgents);
        } catch (error) {
            console.error('Failed to fetch subscribers:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredSubscribers = subscribers.filter(sub => {
        const matchesSearch = sub.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            sub.user_email.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesAgent = selectedAgent === 'all' || sub.agent_id === selectedAgent;
        return matchesSearch && matchesAgent;
    });

    if (loading) {
        return (
            <div className="p-8 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent" />
            </div>
        );
    }

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Subscribers</h1>
                <p className="text-gray-500 mt-1">Manage and view your agent subscribers</p>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-blue-100 rounded-lg">
                                <Users className="w-6 h-6 text-blue-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.total_subscribers}</div>
                                <div className="text-sm text-gray-500">Total Subscribers</div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-green-100 rounded-lg">
                                <CheckCircle className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">{stats.active_licenses}</div>
                                <div className="text-sm text-gray-500">Active Licenses</div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-purple-100 rounded-lg">
                                <TrendingUp className="w-6 h-6 text-purple-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">
                                    ${(stats.monthly_revenue / 100).toFixed(0)}
                                </div>
                                <div className="text-sm text-gray-500">Monthly Revenue</div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-xl p-6 border border-gray-200">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-yellow-100 rounded-lg">
                                <DollarSign className="w-6 h-6 text-yellow-600" />
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-gray-900">
                                    ${(stats.total_revenue / 100).toFixed(0)}
                                </div>
                                <div className="text-sm text-gray-500">Total Revenue</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="bg-white rounded-xl p-6 border border-gray-200 mb-6">
                <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                            <input
                                type="text"
                                placeholder="Search by name or email..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                            />
                        </div>
                    </div>

                    <div className="min-w-[200px]">
                        <div className="relative">
                            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                            <select
                                value={selectedAgent}
                                onChange={(e) => setSelectedAgent(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 appearance-none"
                            >
                                <option value="all">All Agents</option>
                                {agentList.map(agent => (
                                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <button
                        onClick={() => {
                            setSearchQuery('');
                            setSelectedAgent('all');
                        }}
                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        Clear Filters
                    </button>
                </div>
            </div>

            {/* Subscribers Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Subscriber</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Agent</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Start Date</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Renewal</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Revenue</th>
                                <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredSubscribers.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                        {searchQuery || selectedAgent !== 'all'
                                            ? 'No subscribers match your filters.'
                                            : 'No subscribers yet.'}
                                    </td>
                                </tr>
                            ) : (
                                filteredSubscribers.map(sub => (
                                    <tr key={sub.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-gray-900">{sub.user_name}</div>
                                            <div className="text-sm text-gray-500">{sub.user_email}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-gray-900">{sub.agent_name}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={
                                                'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ' +
                                                (sub.license_status === 'ACTIVE'
                                                    ? 'bg-green-100 text-green-700'
                                                    : 'bg-gray-100 text-gray-700')
                                            }>
                                                {sub.license_status === 'ACTIVE' && <CheckCircle className="w-3 h-3" />}
                                                {sub.license_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600">
                                            <div className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4 text-gray-400" />
                                                {new Date(sub.start_date).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600">
                                            {new Date(sub.end_date).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 font-medium text-gray-900">
                                            ${(sub.price_cents / 100).toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex gap-2">
                                                <button
                                                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                                    title="View Details"
                                                >
                                                    <Eye className="w-4 h-4 text-gray-600" />
                                                </button>
                                                <button
                                                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                                    title="Download Report"
                                                >
                                                    <Download className="w-4 h-4 text-gray-600" />
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

            {/* Summary */}
            {filteredSubscribers.length > 0 && (
                <div className="mt-4 text-sm text-gray-500 text-center">
                    Showing {filteredSubscribers.length} of {subscribers.length} subscriber{subscribers.length !== 1 ? 's' : ''}
                </div>
            )}
        </div>
    );
}
