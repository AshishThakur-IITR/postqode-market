import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MultiPlatformDeployWizard } from '../components/MultiPlatformDeployWizard';
import {
    Package, Play, Server, Shield, Clock,
    CheckCircle, ArrowLeft, Tag, Star, Rocket,
    Terminal, ChevronDown, ChevronUp, Copy, Check
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

interface InstallCommands {
    cli: string;
    docker: string;
    helm: string;
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
    const [showDeployWizard, setShowDeployWizard] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [installCommands, setInstallCommands] = useState<InstallCommands | null>(null);
    const [copied, setCopied] = useState('');

    useEffect(() => {
        fetchAgent();
        checkLicense();
    }, [agentId]);

    useEffect(() => {
        if (purchased && agentId) {
            fetchInstallCommands();
        }
    }, [purchased, agentId]);

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

    const checkLicense = async () => {
        if (!user?.id || !agentId) return;
        try {
            const response = await fetch(`/api/v1/market/licenses?user_id=${user.id}&agent_id=${agentId}`);
            if (response.ok) {
                const licenses = await response.json();
                if (licenses.length > 0) {
                    setPurchased(true);
                }
            }
        } catch (err) {
            // Not purchased
        }
    };

    const fetchInstallCommands = async () => {
        try {
            const response = await fetch(`/api/v1/market/agents/${agentId}/install-cmd?adapter=openai`);
            if (response.ok) {
                const data = await response.json();
                setInstallCommands(data);
            }
        } catch (err) {
            // Ignore
        }
    };

    const handlePurchase = async () => {
        if (!user?.id || !agent) return;
        setPurchasing(true);

        try {
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

    const handleDeploySuccess = (deploymentId: string) => {
        console.log('Deployment successful:', deploymentId);
        navigate('/deployments');
    };

    const copyToClipboard = (text: string, key: string) => {
        navigator.clipboard.writeText(text);
        setCopied(key);
        setTimeout(() => setCopied(''), 2000);
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
                                Agent package with all adapters (OpenAI, Anthropic, Azure, Local)
                            </li>
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                Multi-platform deployment (Docker, K8s, Azure, VM, Edge)
                            </li>
                            <li className="flex items-center gap-3 text-gray-700">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                One-click deployment with auto-configuration
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

                                {/* One-Click Deploy Button - PRIMARY ACTION */}
                                <button
                                    onClick={() => setShowDeployWizard(true)}
                                    className="w-full py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-700 flex items-center justify-center gap-2 shadow-lg"
                                >
                                    <Rocket className="w-5 h-5" />
                                    Deploy Now
                                </button>

                                <p className="text-xs text-gray-500 text-center mt-2">
                                    Configure environment & deploy in one click
                                </p>

                                {/* Advanced: CLI Commands (collapsible) */}
                                <div className="mt-6 pt-4 border-t">
                                    <button
                                        onClick={() => setShowAdvanced(!showAdvanced)}
                                        className="w-full flex items-center justify-between text-sm text-gray-600 hover:text-gray-900"
                                    >
                                        <span className="flex items-center gap-2">
                                            <Terminal className="w-4 h-4" />
                                            Manual Install (CLI)
                                        </span>
                                        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </button>

                                    {showAdvanced && installCommands && (
                                        <div className="mt-3 space-y-3">
                                            {/* CLI Command */}
                                            <div className="bg-gray-900 rounded-lg p-3">
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-xs text-green-400">PostQode CLI</span>
                                                    <button
                                                        onClick={() => copyToClipboard(installCommands.cli, 'cli')}
                                                        className="text-gray-400 hover:text-white"
                                                    >
                                                        {copied === 'cli' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                                    </button>
                                                </div>
                                                <code className="text-xs text-gray-100 break-all">{installCommands.cli}</code>
                                            </div>

                                            {/* Docker Command */}
                                            <div className="bg-gray-900 rounded-lg p-3">
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-xs text-blue-400">Docker</span>
                                                    <button
                                                        onClick={() => copyToClipboard(installCommands.docker, 'docker')}
                                                        className="text-gray-400 hover:text-white"
                                                    >
                                                        {copied === 'docker' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                                    </button>
                                                </div>
                                                <code className="text-xs text-gray-100 break-all">{installCommands.docker}</code>
                                            </div>
                                        </div>
                                    )}
                                </div>
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

            {/* Multi-Platform Deploy Wizard Modal */}
            {showDeployWizard && user && (
                <MultiPlatformDeployWizard
                    agentId={agent.id}
                    agentName={agent.name}
                    userId={user.id}
                    onClose={() => setShowDeployWizard(false)}
                    onSuccess={handleDeploySuccess}
                />
            )}
        </div>
    );
}


