import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Cloud, Server, Container, Cpu, Zap, Box,
    ChevronRight, ChevronLeft, Check, Copy, Terminal
} from 'lucide-react';

interface Agent {
    id: string;
    name: string;
    version: string;
    supported_runtimes: string[];
    inputs_schema: any[];
}

interface DeploymentConfig {
    type: string;
    adapter: string;
    environment: string;
    secrets: Record<string, string>;
}

const DEPLOYMENT_TYPES = [
    { id: 'cloud_managed', name: 'PostQode Cloud', icon: Cloud, description: 'Fully managed, instant deployment' },
    { id: 'kubernetes', name: 'Kubernetes', icon: Container, description: 'Deploy to your K8s cluster' },
    { id: 'docker', name: 'Docker', icon: Box, description: 'Run locally with Docker' },
    { id: 'serverless', name: 'Serverless', icon: Zap, description: 'AWS Lambda / Azure Functions' },
    { id: 'vm_standalone', name: 'VM / Bare Metal', icon: Server, description: 'Traditional server deployment' },
    { id: 'edge', name: 'Edge Device', icon: Cpu, description: 'Deploy to IoT/Edge devices' },
];

const ADAPTERS = [
    { id: 'openai', name: 'OpenAI', description: 'GPT-4, GPT-3.5' },
    { id: 'anthropic', name: 'Anthropic', description: 'Claude 3.5, Claude 3' },
    { id: 'azure', name: 'Azure OpenAI', description: 'Enterprise Azure deployment' },
    { id: 'local', name: 'Local LLM', description: 'Ollama, LM Studio' },
];

export function AgentInstallPage() {
    const { agentId } = useParams();
    const navigate = useNavigate();

    const [step, setStep] = useState(1);
    const [agent, setAgent] = useState<Agent | null>(null);
    const [loading, setLoading] = useState(true);
    const [installCommands, setInstallCommands] = useState<any>(null);
    const [copied, setCopied] = useState('');

    const [config, setConfig] = useState<DeploymentConfig>({
        type: 'docker',
        adapter: 'openai',
        environment: 'production',
        secrets: {}
    });

    useEffect(() => {
        if (agentId) {
            fetchAgent();
        }
    }, [agentId]);

    const fetchAgent = async () => {
        try {
            const response = await fetch(`/api/v1/market/agents/${agentId}`);
            const data = await response.json();
            setAgent(data);
        } catch (error) {
            console.error('Failed to fetch agent:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchInstallCommands = async () => {
        try {
            const response = await fetch(
                `/api/v1/market/agents/${agentId}/install-cmd?adapter=${config.adapter}`
            );
            const data = await response.json();
            setInstallCommands(data);
        } catch (error) {
            console.error('Failed to fetch install commands:', error);
        }
    };

    const copyToClipboard = (text: string, key: string) => {
        navigator.clipboard.writeText(text);
        setCopied(key);
        setTimeout(() => setCopied(''), 2000);
    };

    const registerDeployment = async () => {
        // Register deployment with backend
        // In real implementation, this would call POST /deployments
        navigate('/deployments');
    };

    if (loading) {
        return (
            <div className="p-8 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-500 border-t-transparent" />
            </div>
        );
    }

    if (!agent) {
        return <div className="p-8">Agent not found</div>;
    }

    return (
        <div className="p-8 max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Install {agent.name}</h1>
                <p className="text-gray-500 mt-1">Version {agent.version}</p>
            </div>

            {/* Progress Steps */}
            <div className="flex items-center mb-8">
                {['Deployment Type', 'Runtime Adapter', 'Configuration', 'Install'].map((stepName, i) => (
                    <div key={i} className="flex items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${step > i + 1 ? 'bg-green-500 text-white' :
                            step === i + 1 ? 'bg-green-100 text-green-700 border-2 border-green-500' :
                                'bg-gray-100 text-gray-400'
                            }`}>
                            {step > i + 1 ? <Check className="w-4 h-4" /> : i + 1}
                        </div>
                        <span className={`ml-2 text-sm ${step === i + 1 ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                            {stepName}
                        </span>
                        {i < 3 && <ChevronRight className="w-5 h-5 text-gray-300 mx-4" />}
                    </div>
                ))}
            </div>

            {/* Step 1: Deployment Type */}
            {step === 1 && (
                <div>
                    <h2 className="text-xl font-semibold mb-4">Choose Deployment Type</h2>
                    <div className="grid grid-cols-2 gap-4">
                        {DEPLOYMENT_TYPES.map(type => (
                            <button
                                key={type.id}
                                onClick={() => setConfig({ ...config, type: type.id })}
                                className={`p-4 rounded-xl border-2 text-left transition-all ${config.type === type.id
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <type.icon className={`w-8 h-8 mb-2 ${config.type === type.id ? 'text-green-600' : 'text-gray-400'}`} />
                                <div className="font-medium text-gray-900">{type.name}</div>
                                <div className="text-sm text-gray-500">{type.description}</div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Step 2: Runtime Adapter */}
            {step === 2 && (
                <div>
                    <h2 className="text-xl font-semibold mb-4">Select Runtime Adapter</h2>
                    <p className="text-gray-500 mb-6">Choose which LLM provider to use for this agent</p>
                    <div className="space-y-3">
                        {ADAPTERS.map(adapter => (
                            <button
                                key={adapter.id}
                                onClick={() => setConfig({ ...config, adapter: adapter.id })}
                                className={`w-full p-4 rounded-xl border-2 text-left flex items-center justify-between ${config.adapter === adapter.id
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div>
                                    <div className="font-medium text-gray-900">{adapter.name}</div>
                                    <div className="text-sm text-gray-500">{adapter.description}</div>
                                </div>
                                {config.adapter === adapter.id && (
                                    <Check className="w-5 h-5 text-green-600" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Step 3: Configuration */}
            {step === 3 && (
                <div>
                    <h2 className="text-xl font-semibold mb-4">Configure Deployment</h2>
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Environment Name
                            </label>
                            <input
                                type="text"
                                value={config.environment}
                                onChange={(e) => setConfig({ ...config, environment: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg"
                                placeholder="e.g., production, staging"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                API Key ({config.adapter.toUpperCase()})
                            </label>
                            <input
                                type="password"
                                value={config.secrets[`${config.adapter}_key`] || ''}
                                onChange={(e) => setConfig({
                                    ...config,
                                    secrets: { ...config.secrets, [`${config.adapter}_key`]: e.target.value }
                                })}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg"
                                placeholder="Enter your API key"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Your API key is encrypted and stored securely
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Step 4: Install Commands */}
            {step === 4 && (
                <div>
                    <h2 className="text-xl font-semibold mb-4">Install Agent</h2>
                    <p className="text-gray-500 mb-6">Choose your preferred installation method</p>

                    {installCommands && (
                        <div className="space-y-4">
                            {/* CLI Command */}
                            <div className="bg-gray-900 rounded-xl p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-green-400 text-sm font-medium flex items-center gap-2">
                                        <Terminal className="w-4 h-4" />
                                        PostQode CLI
                                    </span>
                                    <button
                                        onClick={() => copyToClipboard(installCommands.cli, 'cli')}
                                        className="text-gray-400 hover:text-white"
                                    >
                                        {copied === 'cli' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                                <code className="text-gray-100 text-sm">{installCommands.cli}</code>
                            </div>

                            {/* Docker Command */}
                            <div className="bg-gray-900 rounded-xl p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-blue-400 text-sm font-medium flex items-center gap-2">
                                        <Box className="w-4 h-4" />
                                        Docker
                                    </span>
                                    <button
                                        onClick={() => copyToClipboard(installCommands.docker, 'docker')}
                                        className="text-gray-400 hover:text-white"
                                    >
                                        {copied === 'docker' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                                <code className="text-gray-100 text-sm">{installCommands.docker}</code>
                            </div>

                            {/* Helm Command */}
                            <div className="bg-gray-900 rounded-xl p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-purple-400 text-sm font-medium flex items-center gap-2">
                                        <Container className="w-4 h-4" />
                                        Helm (Kubernetes)
                                    </span>
                                    <button
                                        onClick={() => copyToClipboard(installCommands.helm, 'helm')}
                                        className="text-gray-400 hover:text-white"
                                    >
                                        {copied === 'helm' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                                <code className="text-gray-100 text-sm">{installCommands.helm}</code>
                            </div>
                        </div>
                    )}

                    <button
                        onClick={registerDeployment}
                        className="mt-6 w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700"
                    >
                        Register Deployment & Track Status
                    </button>
                </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-8 pt-6 border-t">
                <button
                    onClick={() => setStep(s => s - 1)}
                    disabled={step === 1}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 disabled:opacity-30"
                >
                    <ChevronLeft className="w-5 h-5" />
                    Back
                </button>
                {step < 4 && (
                    <button
                        onClick={() => {
                            if (step === 3) fetchInstallCommands();
                            setStep(s => s + 1);
                        }}
                        className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                        Continue
                        <ChevronRight className="w-5 h-5" />
                    </button>
                )}
            </div>
        </div>
    );
}
