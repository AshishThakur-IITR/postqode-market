import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Eye, Server } from 'lucide-react';

interface Agent {
    id: string;
    name: string;
    description: string;
    category: string;
    price_cents: number;
    badge?: string;
    publisher_id: string;
    supported_runtimes?: string[];
    version?: string;
}

export function MarketplacePage() {
    const navigate = useNavigate();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    useEffect(() => {
        fetchAgents();
    }, [search, selectedCategories]);

    const fetchAgents = async () => {
        try {
            const params = new URLSearchParams();
            if (search) params.append('search', search);
            selectedCategories.forEach(c => params.append('category', c));

            const response = await fetch(`/api/v1/market/agents?${params.toString()}`);
            const data = await response.json();
            setAgents(data);
        } catch (error) {
            console.error('Failed to fetch agents:', error);
        } finally {
            setLoading(false);
        }
    };

    const categories = [
        { name: 'Data Analytics', count: 3 },
        { name: 'Finance', count: 2 },
        { name: 'Procurement', count: 2 },
        { name: 'Service Operations', count: 5 }
    ];

    const toggleCategory = (category: string) => {
        if (selectedCategories.includes(category)) {
            setSelectedCategories(selectedCategories.filter(c => c !== category));
        } else {
            setSelectedCategories([...selectedCategories, category]);
        }
    };

    return (
        <div className="p-8 max-w-[1600px] mx-auto">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-bold mb-2">Marketplace</h1>
                <p className="text-gray-500">Discover AI agents and applications for your enterprise</p>
            </div>

            <div className="mb-8 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                    type="text"
                    placeholder="Search agents..."
                    className="w-full pl-12 pr-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <button className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-green-600 text-white px-6 py-1.5 rounded-md text-sm font-medium hover:bg-green-700 transition-colors">
                    Search
                </button>
            </div>

            <div className="flex gap-8">
                {/* Filters Sidebar */}
                <div className="w-64 flex-shrink-0">
                    <div className="mb-6">
                        <h3 className="font-semibold mb-3">Category</h3>
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                                    checked={selectedCategories.length === 0}
                                    onChange={() => setSelectedCategories([])}
                                />
                                <span className="text-sm font-medium">Select All</span>
                            </label>
                            {categories.map(cat => (
                                <label key={cat.name} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                                        checked={selectedCategories.includes(cat.name)}
                                        onChange={() => toggleCategory(cat.name)}
                                    />
                                    <span className="text-sm text-gray-600 flex-1">{cat.name}</span>
                                    <span className="text-xs text-gray-400">({cat.count})</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div className="mb-6">
                        <h3 className="font-semibold mb-3">Price Range: $0 - $1000</h3>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div className="h-full bg-green-500 w-full"></div>
                        </div>
                    </div>

                    <div>
                        <h3 className="font-semibold mb-3">Publisher</h3>
                        <div className="space-y-2">
                            <label className="flex items-center gap-2">
                                <input type="checkbox" className="rounded border-gray-300 text-green-600" defaultChecked />
                                <span className="text-sm text-gray-600 flex-1">PostQode</span>
                                <span className="text-xs text-gray-400">(7)</span>
                            </label>
                            <label className="flex items-center gap-2">
                                <input type="checkbox" className="rounded border-gray-300 text-green-600" defaultChecked />
                                <span className="text-sm text-gray-600 flex-1">Community</span>
                                <span className="text-xs text-gray-400">(5)</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Grid */}
                <div className="flex-1">
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-sm text-gray-500">Showing {agents.length} results</span>
                        <div className="flex gap-2">
                            <select className="border border-gray-200 rounded px-2 py-1 text-sm bg-white">
                                <option>Sort by: Featured</option>
                                <option>Price: Low to High</option>
                                <option>Price: High to Low</option>
                            </select>
                        </div>
                    </div>

                    {loading ? (
                        <div className="text-center py-20 text-gray-500">Loading marketplace...</div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {agents.map(agent => (
                                <div key={agent.id} className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex gap-4">
                                            <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-lg
                                                ${['Finance', 'Procurement'].includes(agent.category) ? 'bg-green-600' :
                                                    agent.category === 'Service Operations' ? 'bg-green-500' :
                                                        agent.category === 'Data Analytics' ? 'bg-teal-500' : 'bg-orange-500'}`}
                                            >
                                                {agent.name.substring(0, 2).toUpperCase()}
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-lg text-gray-900">{agent.name}</h3>
                                                <span className="text-sm text-gray-500">PostQode</span> {/* Simplified publisher for demo */}
                                            </div>
                                        </div>
                                        <span className="bg-[#1E1B4B] text-white text-xs px-2 py-1 rounded">PostQode</span>
                                    </div>

                                    <div className="bg-green-50 text-green-900 text-xs inline-block px-3 py-1 rounded-full font-medium mb-3">
                                        {agent.category}
                                    </div>

                                    <p className="text-sm text-gray-600 mb-4 h-10 line-clamp-2">
                                        {agent.description}
                                    </p>

                                    {/* Runtime badges */}
                                    <div className="flex items-center gap-2 mb-4">
                                        <Server className="w-3 h-3 text-gray-400" />
                                        <div className="flex gap-1">
                                            {(agent.supported_runtimes?.length ? agent.supported_runtimes : ['docker', 'k8s']).slice(0, 2).map(r => (
                                                <span key={r} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                                    {r}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mt-auto">
                                        <span className="text-xl font-bold text-gray-900">${agent.price_cents / 100}</span>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => navigate('/agent/' + agent.id)}
                                                className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                                                title="View Details"
                                            >
                                                <Eye className="w-4 h-4 text-gray-600" />
                                            </button>
                                            <button
                                                onClick={() => navigate('/agent/' + agent.id)}
                                                className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                                            >
                                                Get it Now
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
