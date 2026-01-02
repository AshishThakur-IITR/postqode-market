import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Search, Eye, Download, Bell, ChevronRight, MessageSquare, Package } from 'lucide-react';

interface DashboardData {
    action_required: any[];
    renewals_due: any[];
    my_agents: any[];
}

export function DashboardPage() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [downloading, setDownloading] = useState<string | null>(null);

    useEffect(() => {
        if (user?.id) {
            fetchData();
        }
    }, [user?.id]);

    const fetchData = async () => {
        try {
            const response = await fetch('/api/v1/market/dashboard?user_id=' + user?.id);
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (agentId: string) => {
        if (!user?.id) return;
        setDownloading(agentId);
        try {
            // Navigate to install page for this agent
            navigate('/install/' + agentId);
        } finally {
            setDownloading(null);
        }
    };

    const handleViewAgent = (agentId: string) => {
        navigate('/agent/' + agentId);
    };

    const filteredAgents = data?.my_agents.filter(agent =>
        agent.name.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

    if (loading) return <div className="p-8 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent" /></div>;
    if (!data) return <div className="p-8 text-center text-gray-500">Failed to load dashboard data.</div>;

    return (
        <div className="p-8 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
                <p className="text-gray-500">Access and manage your AI agents and licenses</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Action Required */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="font-bold text-gray-900">Action Required</h2>
                        <button
                            onClick={() => navigate('/deployments')}
                            className="text-sm text-green-600 font-medium hover:underline"
                        >
                            View All →
                        </button>
                    </div>
                    <div className="space-y-3">
                        {data.action_required.length > 0 && (
                            <div className="flex items-center gap-2 mb-2">
                                <span className="font-medium text-sm">Download Available</span>
                                <span className="bg-green-600 text-white text-xs w-5 h-5 flex items-center justify-center rounded-full">
                                    {data.action_required.length}
                                </span>
                            </div>
                        )}
                        {data.action_required.length === 0 ? (
                            <p className="text-sm text-gray-500">No actions required.</p>
                        ) : (
                            data.action_required.map((item: any) => (
                                <div key={item.id} className="flex items-center justify-between p-3 border border-gray-100 rounded-lg bg-gray-50">
                                    <div>
                                        <h3 className="font-bold text-sm">{item.agent_name}</h3>
                                        <p className="text-xs text-gray-500">v{item.agent_version} • {item.type}</p>
                                    </div>
                                    <button
                                        onClick={() => handleDownload(item.id)}
                                        className="p-2 hover:bg-green-100 rounded-lg transition-colors"
                                        title="Download & Install"
                                    >
                                        <Download className={`w-5 h-5 ${downloading === item.id ? 'animate-pulse text-green-600' : 'text-gray-400 hover:text-green-600'}`} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Renewals Due */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="font-bold text-gray-900">Renewals Due</h2>
                        <button
                            onClick={() => navigate('/deployments')}
                            className="text-sm text-green-600 font-medium hover:underline"
                        >
                            View All →
                        </button>
                    </div>
                    <div className="space-y-3">
                        {data.renewals_due.length === 0 ? (
                            <p className="text-sm text-gray-500">No renewals due.</p>
                        ) : (
                            data.renewals_due.map((renewal: any) => (
                                <div key={renewal.id} className="p-4 bg-orange-50 border border-orange-100 rounded-lg relative">
                                    <Bell className="absolute top-4 right-4 w-4 h-4 text-orange-400" />
                                    <h3 className="font-bold text-sm text-gray-900">{renewal.agent_name}</h3>
                                    <p className="text-xs text-orange-600 font-medium mt-1">by {renewal.publisher}</p>
                                    <p className="text-xs text-gray-600 mt-2">
                                        Renewal: <span className="font-medium">{new Date(renewal.renewal_date).toLocaleDateString()}</span>
                                        <span className="text-red-500 ml-1">({renewal.days_remaining} days)</span>
                                    </p>
                                    <button
                                        onClick={() => handleViewAgent(renewal.id)}
                                        className="mt-2 text-xs text-green-600 hover:underline"
                                    >
                                        View Details →
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Explore Marketplace */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                    <h2 className="font-bold text-gray-900 mb-4">Explore Marketplace</h2>
                    <div className="space-y-3">
                        <button
                            onClick={() => navigate('/marketplace')}
                            className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <Package className="w-5 h-5 text-green-600" />
                                <span className="font-medium text-sm">Browse All Agents</span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                            onClick={() => navigate('/marketplace?sort=popular')}
                            className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            <span className="font-medium text-sm">Popular Solutions</span>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                            onClick={() => navigate('/marketplace?sort=newest')}
                            className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            <span className="font-medium text-sm">New Arrivals</span>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                </div>
            </div>

            {/* My Agents */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-2">
                        <h2 className="font-bold text-lg text-gray-900">My Agents</h2>
                        <span className="text-gray-500">({data.my_agents.length})</span>
                    </div>
                    <div className="flex gap-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <input
                                type="text"
                                placeholder="Search agents..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                            />
                        </div>
                        <button
                            onClick={() => navigate('/marketplace')}
                            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                        >
                            + Add Agent
                        </button>
                    </div>
                </div>

                {filteredAgents.length === 0 ? (
                    <div className="text-center py-12">
                        <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500 mb-4">
                            {searchQuery ? 'No agents match your search.' : 'No licensed agents yet.'}
                        </p>
                        <button
                            onClick={() => navigate('/marketplace')}
                            className="text-green-600 hover:underline font-medium"
                        >
                            Browse Marketplace →
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredAgents.map((agent: any) => (
                            <div key={agent.id} className="border border-gray-200 rounded-xl p-5 bg-gray-50/50 hover:shadow-md transition-shadow">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-3">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-sm ${['Finance', 'Procurement'].includes(agent.category) ? 'bg-green-600' :
                                                agent.category === 'Service Operations' ? 'bg-green-500' :
                                                    agent.category === 'Data Analytics' ? 'bg-teal-500' : 'bg-orange-500'
                                            }`}>
                                            {agent.name.substring(0, 2).toUpperCase()}
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-900 text-sm">{agent.name}</h3>
                                            <span className="text-xs text-gray-500">PostQode</span>
                                        </div>
                                    </div>
                                    <span className="bg-[#1E1B4B] text-white text-[10px] px-1.5 py-0.5 rounded">PostQode</span>
                                </div>

                                <div className="bg-green-100 text-green-900 text-[10px] inline-block px-2 py-0.5 rounded-full font-medium mb-3">
                                    {agent.category}
                                </div>

                                <p className="text-sm font-medium text-gray-700 mb-3">${(agent.price_cents / 100).toFixed(2)}/year</p>

                                <div className="mb-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="w-4 h-4 rounded-full bg-green-600 text-white flex items-center justify-center text-[10px] font-bold">!</span>
                                        <span className="text-xs font-medium text-green-700">
                                            Usage: {agent.usage_percentage}% ({agent.sessions_used}/{agent.sessions_total} sessions)
                                        </span>
                                    </div>
                                    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                        <div className="h-full bg-green-600 transition-all" style={{ width: agent.usage_percentage + '%' }} />
                                    </div>
                                </div>

                                <div className="border-t border-gray-200 pt-3 flex items-center justify-between">
                                    <div className="text-[10px] text-gray-500">
                                        <div>Status: <span className="text-green-600 font-medium">{agent.status}</span></div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleViewAgent(agent.id)}
                                            className="p-1.5 border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                                            title="View Details"
                                        >
                                            <Eye className="w-4 h-4 text-gray-600" />
                                        </button>
                                        <button
                                            onClick={() => handleDownload(agent.id)}
                                            className="p-1.5 border border-gray-200 rounded-lg bg-white hover:bg-green-50"
                                            title="Download & Install"
                                        >
                                            <Download className="w-4 h-4 text-green-600" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Chat Widget */}
            <div className="fixed bottom-6 right-6">
                <button className="bg-green-700 text-white p-4 rounded-full shadow-lg hover:bg-green-800 transition-colors">
                    <MessageSquare className="w-6 h-6" />
                </button>
            </div>
        </div>
    );
}
