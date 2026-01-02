import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    Package, Download, Play, Server, Shield, Clock,
    CheckCircle, ArrowLeft, Tag, Star
} from 'lucide-react';

interface AgentDetail {
    id: string;
    name: string;
    description: string;
    category: string;
    price_cents: number;
    version: string;
    status: string;
    publisher_id: string;
    supported_runtimes: string[];
    required_permissions: Record<string, any>;
    min_runtime_version: string;
    inputs_schema: any[];
    outputs_schema: any[];
    created_at: string;
}

const RUNTIME_ICONS: Record<string, string> = {
    docker: '🐳',
    kubernetes: '☸️',
    python: '🐍',
    nodejs: '💚',
    serverless: '⚡',
};

export function AgentDetailPage() {
    const { agentId } = useParams<{ agentId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const [agent, setAgent] = useState<AgentDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [purchasing, setPurchasing] = useState(false);
    const [purchased, setPurchased] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchAgent();
    }, [agentId]);

    const fetchAgent = async () => {
        try {
            const response = await fetch('/api/v1/market/agents/' + agentId);
            if (!response.ok) throw new Error('Agent not found');
            const data = await response.json();
            setAgent(data);
        } catch (err) {
            setError('Failed to load agent');
        } finally {
            setLoading(false);
        }
    };

    const handlePurchase = async () => {
        if (!user?.id || !agent) return;
        setPurchasing(true);

        try {
            // Create license for the user
            const response = await fetch('/api/v1/market/licenses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.id,
                    agent_id: agent.id,
                    license_type: 'standard'
                })
            });

            if (!response.ok) throw new Error('Purchase failed');
            setPurchased(true);
        } catch (err) {
            setError('Purchase failed. Please try again.');
        } finally {
            setPurchasing(false);
        }
    };

    const handleDownload = async () => {
        if (!user?.id || !agent) return;

        // Navigate to install page with agent context
        navigate('/install/' + agent.id);
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent"></div>
            </div>
        );
    }

    if (error || !agent) {
        return (
            <div className="p-8 max-w-4xl mx-auto">
                <div className="bg-red-50 p-6 rounded-xl text-center">
                    <p className="text-red-600">{error || 'Agent not found'}</p>
                    <button onClick={() => navigate('/marketplace')} className="mt-4 text-green-600 hover:underline">
                        Back to Marketplace
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-5xl mx-auto">
            {/* Back Button */}
            <button
                onClick={() => navigate('/marketplace')}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Marketplace
            </button>

            <div className="grid grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="col-span-2 space-y-6">
                    {/* Header */}
                    <div className="bg-white rounded-xl p-6 border">
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="w-14 h-14 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center">
                                        <Package className="w-7 h-7 text-white" />
                                    </div>
                                    <div>
                                        <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
                                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                                            {agent.category}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-3xl font-bold text-gray-900">
                                    ${(agent.price_cents / 100).toFixed(2)}
                                </div>
                                <div className="text-sm text-gray-500">per month</div>
                            </div>
                        </div>

                        <p className="text-gray-600 mt-4 leading-relaxed">{agent.description}</p>

                        <div className="flex items-center gap-6 mt-4 text-sm text-gray-500">
                            <div className="flex items-center gap-1">
                                <Tag className="w-4 h-4" />
                                v{agent.version}
                            </div>
                            <div className="flex items-center gap-1">
                                <Star className="w-4 h-4 text-yellow-500" />
                                4.8 (128 reviews)
                            </div>
                        </div>
                    </div>

                    {/* Runtime Requirements */}
                    <div className="bg-white rounded-xl p-6 border">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Server className="w-5 h-5 text-green-600" />
                            Runtime Requirements
                        </h2>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-gray-50 rounded-lg">
                                <div className="text-sm text-gray-500 mb-2">Supported Runtimes</div>
                                <div className="flex flex-wrap gap-2">
                                    {(agent.supported_runtimes?.length > 0 ? agent.supported_runtimes : ['docker', 'kubernetes']).map(runtime => (
                                        <span key={runtime} className="inline-flex items-center gap-1 px-3 py-1 bg-white border rounded-full text-sm">
                                            {RUNTIME_ICONS[runtime] || '📦'} {runtime}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="p-4 bg-gray-50 rounded-lg">
                                <div className="text-sm text-gray-500 mb-2">Min Runtime Version</div>
                                <div className="text-lg font-medium">{agent.min_runtime_version || '1.0.0'}</div>
                            </div>
                        </div>

                        {agent.required_permissions && Object.keys(agent.required_permissions).length > 0 && (
                            <div className="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                                <div className="text-sm font-medium text-yellow-800 mb-2 flex items-center gap-2">
                                    <Shield className="w-4 h-4" />
                                    Required Permissions
                                </div>
                                <ul className="text-sm text-yellow-700 space-y-1">
                                    {Object.entries(agent.required_permissions).map(([key, val]) => (
                                        <li key={key}>• {key}: {String(val)}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    {/* What's Included */}
                    <div className="bg-white rounded-xl p-6 border">
                        <h2 className="text-lg font-semibold mb-4">What's Included</h2>
                        <ul className="space-y-3">
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                Agent package with all adapters
                            </li>
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                Docker and Kubernetes deployment configs
                            </li>
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                30-day money back guarantee
                            </li>
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                Free updates for 1 year
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Sidebar - Purchase Card */}
                <div className="col-span-1">
                    <div className="bg-white rounded-xl p-6 border sticky top-8">
                        <div className="text-center mb-6">
                            <div className="text-3xl font-bold text-gray-900">
                                ${(agent.price_cents / 100).toFixed(2)}
                            </div>
                            <div className="text-sm text-gray-500">per month</div>
                        </div>

                        {purchased ? (
                            <>
                                <div className="mb-4 p-3 bg-green-50 rounded-lg text-center">
                                    <CheckCircle className="w-6 h-6 text-green-600 mx-auto mb-1" />
                                    <span className="text-green-700 font-medium">License Activated!</span>
                                </div>
                                <button
                                    onClick={handleDownload}
                                    className="w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 flex items-center justify-center gap-2"
                                >
                                    <Download className="w-5 h-5" />
                                    Download & Install
                                </button>
                            </>
                        ) : (
                            <button
                                onClick={handlePurchase}
                                disabled={purchasing}
                                className="w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {purchasing ? (
                                    <>
                                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                                        Processing...
                                    </>
                                ) : (
                                    <>
                                        <Play className="w-5 h-5" />
                                        Buy Now
                                    </>
                                )}
                            </button>
                        )}

                        <div className="mt-6 pt-6 border-t space-y-3 text-sm">
                            <div className="flex items-center gap-2 text-gray-600">
                                <Shield className="w-4 h-4" />
                                Secure checkout
                            </div>
                            <div className="flex items-center gap-2 text-gray-600">
                                <Clock className="w-4 h-4" />
                                Instant access after purchase
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
