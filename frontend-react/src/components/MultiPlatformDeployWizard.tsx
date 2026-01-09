/**
 * Multi-Platform Deploy Wizard
 * Supports Docker, Kubernetes, Azure Functions, VM, and Edge deployments
 */
import React, { useState, useEffect } from 'react';
import {
    Box, Container, Cloud, Server, Cpu, Zap,
    ChevronRight, ChevronLeft, Check, X, AlertCircle,
    Eye, EyeOff, Loader2, ExternalLink, Copy, Terminal
} from 'lucide-react';

interface Platform {
    id: string;
    name: string;
    description: string;
    icon: string;
    available: boolean;
    requirements: Record<string, boolean>;
    config_schema: ConfigSchema;
}

interface ConfigSchema {
    type: string;
    properties: Record<string, PropertySchema>;
    required?: string[];
}

interface PropertySchema {
    type: string;
    description?: string;
    default?: any;
    enum?: string[];
    format?: string;
    minimum?: number;
    maximum?: number;
}

interface DeployWizardProps {
    agentId: string;
    agentName: string;
    userId: string;
    onClose: () => void;
    onSuccess: (deploymentId: string) => void;
}

interface DeploymentStep {
    step: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    message: string;
}

const PLATFORM_ICONS: Record<string, React.ComponentType<any>> = {
    box: Box,
    container: Container,
    cloud: Cloud,
    server: Server,
    cpu: Cpu,
    zap: Zap,
};

const ADAPTERS = [
    { id: 'openai', name: 'OpenAI', description: 'GPT-4o, GPT-4, GPT-3.5' },
    { id: 'anthropic', name: 'Anthropic', description: 'Claude 3.5, Claude 3' },
    { id: 'azure', name: 'Azure OpenAI', description: 'Enterprise Azure' },
    { id: 'local', name: 'Local LLM', description: 'Ollama, LM Studio' },
];

export function MultiPlatformDeployWizard({
    agentId,
    agentName,
    userId,
    onClose,
    onSuccess
}: DeployWizardProps) {
    const [step, setStep] = useState(1);
    const [platforms, setPlatforms] = useState<Platform[]>([]);
    const [loading, setLoading] = useState(true);
    const [deploying, setDeploying] = useState(false);
    const [error, setError] = useState('');

    // Configuration state
    const [selectedPlatform, setSelectedPlatform] = useState('docker');
    const [selectedAdapter, setSelectedAdapter] = useState('openai');
    const [envVars, setEnvVars] = useState<Record<string, string>>({});
    const [platformConfig, setPlatformConfig] = useState<Record<string, any>>({});
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
    const [port, setPort] = useState(8080);

    // Deployment result
    const [deploymentSteps, setDeploymentSteps] = useState<DeploymentStep[]>([]);
    const [deploymentResult, setDeploymentResult] = useState<any>(null);

    useEffect(() => {
        fetchPlatforms();
        fetchEnvRequirements();
    }, [agentId]);

    const fetchPlatforms = async () => {
        try {
            const response = await fetch('/api/v1/unified/platforms');
            if (response.ok) {
                const data = await response.json();
                setPlatforms(data.platforms);
            }
        } catch (err) {
            console.error('Failed to fetch platforms:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchEnvRequirements = async () => {
        try {
            const response = await fetch(`/api/v1/unified/agents/${agentId}/env-requirements`);
            if (response.ok) {
                const data = await response.json();
                // Pre-populate required env vars
                const adapterVars = data.adapter_env_vars[selectedAdapter] || [];
                const initialEnv: Record<string, string> = {};
                adapterVars.forEach((v: any) => {
                    if (v.default) initialEnv[v.key] = v.default;
                });
                setEnvVars(initialEnv);
            }
        } catch (err) {
            console.error('Failed to fetch env requirements:', err);
        }
    };

    const handleDeploy = async () => {
        setDeploying(true);
        setError('');
        setDeploymentSteps([]);

        try {
            const response = await fetch(`/api/v1/unified/deploy?user_id=${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_id: agentId,
                    adapter: selectedAdapter,
                    deployment_type: selectedPlatform,
                    port: port,
                    env_vars: envVars,
                    platform_config: platformConfig,
                    auto_start: true
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || result.detail || 'Deployment failed');
            }

            setDeploymentSteps(result.steps || []);
            setDeploymentResult(result);
            setStep(4);

            if (result.deployment_id) {
                onSuccess(result.deployment_id);
            }
        } catch (err: any) {
            setError(err.message);
        } finally {
            setDeploying(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const renderPlatformIcon = (iconName: string) => {
        const IconComponent = PLATFORM_ICONS[iconName] || Box;
        return <IconComponent className="w-8 h-8" />;
    };

    const selectedPlatformData = platforms.find(p => p.id === selectedPlatform);

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white rounded-2xl p-8 flex items-center gap-3">
                    <Loader2 className="w-6 h-6 animate-spin text-green-600" />
                    <span>Loading deployment options...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b bg-gradient-to-r from-green-500 to-emerald-600 text-white">
                    <div className="flex justify-between items-center">
                        <div>
                            <h2 className="text-2xl font-bold">Deploy {agentName}</h2>
                            <p className="text-green-100">Choose your deployment platform</p>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg">
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Step indicator */}
                    <div className="flex items-center gap-2 mt-4">
                        {['Platform', 'Adapter', 'Configuration', 'Deploy'].map((s, i) => (
                            <React.Fragment key={s}>
                                <div className={`flex items-center gap-2 ${i + 1 <= step ? 'text-white' : 'text-green-200'}`}>
                                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i + 1 < step ? 'bg-white text-green-600' :
                                        i + 1 === step ? 'bg-white/20 border-2 border-white' :
                                            'bg-green-400/30'
                                        }`}>
                                        {i + 1 < step ? <Check className="w-4 h-4" /> : i + 1}
                                    </div>
                                    <span className="text-sm hidden sm:inline">{s}</span>
                                </div>
                                {i < 3 && <ChevronRight className="w-4 h-4 text-green-200" />}
                            </React.Fragment>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {error && (
                        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Step 1: Platform Selection */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold">Select Deployment Platform</h3>
                            <div className="grid grid-cols-2 gap-4">
                                {platforms.map(platform => (
                                    <button
                                        key={platform.id}
                                        onClick={() => setSelectedPlatform(platform.id)}
                                        disabled={!platform.available}
                                        className={`p-4 rounded-xl border-2 text-left transition-all ${selectedPlatform === platform.id
                                            ? 'border-green-500 bg-green-50'
                                            : platform.available
                                                ? 'border-gray-200 hover:border-gray-300'
                                                : 'border-gray-100 opacity-50 cursor-not-allowed'
                                            }`}
                                    >
                                        <div className={`mb-2 ${selectedPlatform === platform.id ? 'text-green-600' : 'text-gray-400'}`}>
                                            {renderPlatformIcon(platform.icon)}
                                        </div>
                                        <div className="font-medium text-gray-900">{platform.name}</div>
                                        <div className="text-sm text-gray-500">{platform.description}</div>
                                        {!platform.available && (
                                            <div className="text-xs text-amber-600 mt-2">
                                                Prerequisites not met
                                            </div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Adapter Selection */}
                    {step === 2 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold">Select LLM Adapter</h3>
                            <p className="text-gray-500">Choose which AI provider to use</p>
                            <div className="space-y-3">
                                {ADAPTERS.map(adapter => (
                                    <button
                                        key={adapter.id}
                                        onClick={() => setSelectedAdapter(adapter.id)}
                                        className={`w-full p-4 rounded-xl border-2 text-left flex items-center justify-between ${selectedAdapter === adapter.id
                                            ? 'border-green-500 bg-green-50'
                                            : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                    >
                                        <div>
                                            <div className="font-medium text-gray-900">{adapter.name}</div>
                                            <div className="text-sm text-gray-500">{adapter.description}</div>
                                        </div>
                                        {selectedAdapter === adapter.id && (
                                            <Check className="w-5 h-5 text-green-600" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Configuration */}
                    {step === 3 && (
                        <div className="space-y-6">
                            <h3 className="text-lg font-semibold">Configure Deployment</h3>

                            {/* Platform-specific config */}
                            {selectedPlatformData?.config_schema && (
                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-700 flex items-center gap-2">
                                        {renderPlatformIcon(selectedPlatformData.icon)}
                                        {selectedPlatformData.name} Configuration
                                    </h4>
                                    <div className="grid gap-4">
                                        {Object.entries(selectedPlatformData.config_schema.properties || {}).map(([key, prop]) => (
                                            <div key={key}>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                    {selectedPlatformData.config_schema.required?.includes(key) && (
                                                        <span className="text-red-500 ml-1">*</span>
                                                    )}
                                                </label>
                                                {prop.enum ? (
                                                    <select
                                                        value={platformConfig[key] || prop.default || ''}
                                                        onChange={(e) => setPlatformConfig({ ...platformConfig, [key]: e.target.value })}
                                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                                                    >
                                                        <option value="">Select...</option>
                                                        {prop.enum.map(opt => (
                                                            <option key={opt} value={opt}>{opt}</option>
                                                        ))}
                                                    </select>
                                                ) : prop.type === 'boolean' ? (
                                                    <label className="flex items-center gap-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={platformConfig[key] ?? prop.default ?? false}
                                                            onChange={(e) => setPlatformConfig({ ...platformConfig, [key]: e.target.checked })}
                                                            className="w-4 h-4 text-green-600 rounded"
                                                        />
                                                        <span className="text-sm text-gray-600">{prop.description}</span>
                                                    </label>
                                                ) : prop.type === 'integer' ? (
                                                    <input
                                                        type="number"
                                                        value={platformConfig[key] ?? prop.default ?? ''}
                                                        onChange={(e) => setPlatformConfig({ ...platformConfig, [key]: parseInt(e.target.value) })}
                                                        min={prop.minimum}
                                                        max={prop.maximum}
                                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                                                        placeholder={prop.description}
                                                    />
                                                ) : prop.format === 'base64' ? (
                                                    <div className="space-y-2">
                                                        {key === 'kubeconfig' && (
                                                            <button
                                                                type="button"
                                                                onClick={async () => {
                                                                    try {
                                                                        const resp = await fetch('/api/v1/unified/kubeconfig');
                                                                        if (resp.ok) {
                                                                            const data = await resp.json();
                                                                            setPlatformConfig({ ...platformConfig, [key]: data.kubeconfig_base64 });
                                                                        } else {
                                                                            setError('No local kubeconfig found');
                                                                        }
                                                                    } catch (e) {
                                                                        setError('Failed to read local kubeconfig');
                                                                    }
                                                                }}
                                                                className="px-3 py-1.5 bg-blue-100 text-blue-700 text-sm rounded-lg hover:bg-blue-200 flex items-center gap-2"
                                                            >
                                                                <Terminal className="w-4 h-4" />
                                                                Use Local Config (~/.kube/config)
                                                            </button>
                                                        )}
                                                        <textarea
                                                            value={platformConfig[key] || ''}
                                                            onChange={(e) => setPlatformConfig({ ...platformConfig, [key]: e.target.value })}
                                                            className="w-full px-3 py-2 border border-gray-200 rounded-lg font-mono text-sm"
                                                            rows={3}
                                                            placeholder={platformConfig[key] ? 'Kubeconfig loaded ✓' : prop.description}
                                                        />
                                                        {platformConfig[key] && (
                                                            <p className="text-xs text-green-600">✓ Kubeconfig loaded ({platformConfig[key].length} characters)</p>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <input
                                                        type="text"
                                                        value={platformConfig[key] ?? prop.default ?? ''}
                                                        onChange={(e) => setPlatformConfig({ ...platformConfig, [key]: e.target.value })}
                                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                                                        placeholder={prop.description}
                                                    />
                                                )}
                                                {prop.description && prop.type !== 'boolean' && (
                                                    <p className="text-xs text-gray-500 mt-1">{prop.description}</p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Port (for applicable platforms) */}
                            {['docker', 'vm_standalone'].includes(selectedPlatform) && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                                    <input
                                        type="number"
                                        value={port}
                                        onChange={(e) => setPort(parseInt(e.target.value))}
                                        className="w-32 px-3 py-2 border border-gray-200 rounded-lg"
                                    />
                                </div>
                            )}

                            {/* Environment Variables */}
                            <div>
                                <h4 className="font-medium text-gray-700 mb-3">Environment Variables</h4>
                                <div className="space-y-3">
                                    {/* API Key based on adapter */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            {selectedAdapter.toUpperCase()} API Key
                                            <span className="text-red-500 ml-1">*</span>
                                        </label>
                                        <div className="relative">
                                            <input
                                                type={showSecrets['api_key'] ? 'text' : 'password'}
                                                value={envVars[`${selectedAdapter.toUpperCase()}_API_KEY`] || envVars.OPENAI_API_KEY || ''}
                                                onChange={(e) => setEnvVars({
                                                    ...envVars,
                                                    [`${selectedAdapter.toUpperCase()}_API_KEY`]: e.target.value,
                                                    OPENAI_API_KEY: selectedAdapter === 'openai' ? e.target.value : (envVars.OPENAI_API_KEY || '')
                                                })}
                                                className="w-full px-3 py-2 pr-10 border border-gray-200 rounded-lg"
                                                placeholder="Enter your API key"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowSecrets({ ...showSecrets, api_key: !showSecrets['api_key'] })}
                                                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                            >
                                                {showSecrets['api_key'] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Deployment Result */}
                    {step === 4 && (
                        <div className="space-y-6">
                            <div className={`p-4 rounded-xl ${deploymentResult?.status === 'active' ? 'bg-green-50' : 'bg-amber-50'}`}>
                                <h3 className={`text-lg font-semibold ${deploymentResult?.status === 'active' ? 'text-green-700' : 'text-amber-700'}`}>
                                    {deploymentResult?.status === 'active' ? '🎉 Deployment Successful!' : 'Deployment Status'}
                                </h3>
                            </div>

                            {/* Steps */}
                            <div className="space-y-2">
                                {deploymentSteps.map((s, i) => (
                                    <div key={i} className={`flex items-center gap-3 p-3 rounded-lg ${s.status === 'completed' ? 'bg-green-50' :
                                        s.status === 'failed' ? 'bg-red-50' :
                                            'bg-gray-50'
                                        }`}>
                                        {s.status === 'completed' ? (
                                            <Check className="w-5 h-5 text-green-500" />
                                        ) : s.status === 'failed' ? (
                                            <AlertCircle className="w-5 h-5 text-red-500" />
                                        ) : (
                                            <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
                                        )}
                                        <span className="text-sm">{s.message}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Access URL */}
                            {deploymentResult?.container_url && (
                                <div className="bg-gray-900 rounded-xl p-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-green-400 text-sm font-medium flex items-center gap-2">
                                            <Terminal className="w-4 h-4" />
                                            Access URL
                                        </span>
                                        <button
                                            onClick={() => copyToClipboard(deploymentResult.container_url)}
                                            className="text-gray-400 hover:text-white"
                                        >
                                            <Copy className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <code className="text-gray-100 text-sm">{deploymentResult.container_url}</code>
                                        <a
                                            href={deploymentResult.container_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-blue-400 hover:text-blue-300"
                                        >
                                            <ExternalLink className="w-4 h-4" />
                                        </a>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t flex justify-between bg-gray-50">
                    <button
                        onClick={() => step > 1 ? setStep(s => s - 1) : onClose()}
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        {step === 1 ? 'Cancel' : 'Back'}
                    </button>

                    {step < 3 && (
                        <button
                            onClick={() => setStep(s => s + 1)}
                            className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                        >
                            Continue
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    )}

                    {step === 3 && (
                        <button
                            onClick={handleDeploy}
                            disabled={deploying}
                            className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                        >
                            {deploying ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Deploying...
                                </>
                            ) : (
                                <>
                                    Deploy Now
                                    <ChevronRight className="w-5 h-5" />
                                </>
                            )}
                        </button>
                    )}

                    {step === 4 && (
                        <button
                            onClick={onClose}
                            className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                        >
                            <Check className="w-5 h-5" />
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default MultiPlatformDeployWizard;
