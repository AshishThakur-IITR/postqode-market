import { useState, useEffect } from 'react';
import {
    X, ChevronRight, ChevronLeft, Check, Loader2, AlertCircle,
    Rocket, Settings, Key, ExternalLink, Eye, EyeOff
} from 'lucide-react';

interface EnvVar {
    key: string;
    description?: string;
    required?: boolean;
    secret?: boolean;
    default?: string;
    auto_set?: boolean;
    value?: string;
}

interface EnvRequirements {
    agent_id: string;
    agent_name: string;
    required_env_vars: EnvVar[];
    optional_env_vars: EnvVar[];
    supported_adapters: string[];
    adapter_env_vars: Record<string, EnvVar[]>;
}

interface DeploymentStep {
    step: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    message: string;
}

interface DeploymentResponse {
    deployment_id: string;
    status: string;
    steps: DeploymentStep[];
    container_url?: string;
    error?: string;
}

interface Agent {
    id: string;
    name: string;
    version: string;
    description: string;
}

interface UnifiedDeployWizardProps {
    agent: Agent;
    userId: string;
    onClose: () => void;
    onSuccess: (deploymentId: string) => void;
}

const ADAPTERS = [
    { id: 'openai', name: 'OpenAI', description: 'GPT-4, GPT-3.5-Turbo', icon: '🤖' },
    { id: 'anthropic', name: 'Anthropic', description: 'Claude 3.5, Claude 3', icon: '🧠' },
    { id: 'azure', name: 'Azure OpenAI', description: 'Enterprise Azure', icon: '☁️' },
    { id: 'local', name: 'Local LLM', description: 'Ollama, LM Studio', icon: '💻' },
];

// Deployment types reserved for future use
// const DEPLOYMENT_TYPES = [
//     { id: 'docker', name: 'Docker', description: 'Local container' },
//     { id: 'kubernetes', name: 'Kubernetes', description: 'K8s cluster' },
//     { id: 'cloud_managed', name: 'PostQode Cloud', description: 'Fully managed' },
// ];

export function UnifiedDeployWizard({ agent, userId, onClose, onSuccess }: UnifiedDeployWizardProps) {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [deploying, setDeploying] = useState(false);
    const [envRequirements, setEnvRequirements] = useState<EnvRequirements | null>(null);
    const [deploymentResult, setDeploymentResult] = useState<DeploymentResponse | null>(null);
    const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

    // Configuration state
    const [config, setConfig] = useState({
        adapter: 'openai',
        deploymentType: 'docker',
        environmentName: 'production',
        port: 8080,
        envVars: {} as Record<string, string>,
    });

    useEffect(() => {
        fetchEnvRequirements();
    }, [agent.id]);

    const fetchEnvRequirements = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/v1/unified/agents/${agent.id}/env-requirements`);
            if (response.ok) {
                const data = await response.json();
                setEnvRequirements(data);
            }
        } catch (error) {
            console.error('Failed to fetch env requirements:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleEnvChange = (key: string, value: string) => {
        setConfig(prev => ({
            ...prev,
            envVars: { ...prev.envVars, [key]: value }
        }));
    };

    const toggleSecretVisibility = (key: string) => {
        setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const getAdapterEnvVars = (): EnvVar[] => {
        if (!envRequirements) return [];
        return envRequirements.adapter_env_vars[config.adapter] || [];
    };

    const validateConfig = (): boolean => {
        const adapterVars = getAdapterEnvVars();
        for (const v of adapterVars) {
            if (v.required && !config.envVars[v.key]) {
                return false;
            }
        }
        return true;
    };

    const handleDeploy = async () => {
        setDeploying(true);
        try {
            const response = await fetch(`/api/v1/unified/deploy?user_id=${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_id: agent.id,
                    adapter: config.adapter,
                    deployment_type: config.deploymentType,
                    environment_name: config.environmentName,
                    port: config.port,
                    env_vars: config.envVars,
                    auto_start: true
                })
            });

            const data = await response.json();
            setDeploymentResult(data);

            if (data.status === 'active') {
                onSuccess(data.deployment_id);
            }
        } catch (error) {
            console.error('Deployment failed:', error);
            setDeploymentResult({
                deployment_id: '',
                status: 'failed',
                steps: [{
                    step: 'deploy',
                    status: 'failed',
                    message: 'Network error'
                }],
                error: 'Failed to connect to server'
            });
        } finally {
            setDeploying(false);
        }
    };

    const renderEnvVarInput = (v: EnvVar, isSecret: boolean = false) => {
        const isVisible = showSecrets[v.key];
        return (
            <div key={v.key} className="mb-4">
                <div className="flex items-center justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                        {isSecret && <Key className="w-3 h-3 text-yellow-600" />}
                        {v.key}
                        {v.required && <span className="text-red-500">*</span>}
                    </label>
                    {isSecret && (
                        <button
                            type="button"
                            onClick={() => toggleSecretVisibility(v.key)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    )}
                </div>
                <input
                    type={isSecret && !isVisible ? 'password' : 'text'}
                    value={config.envVars[v.key] || ''}
                    onChange={(e) => handleEnvChange(v.key, e.target.value)}
                    placeholder={v.default || v.description || `Enter ${v.key}`}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-sm"
                />
                {v.description && (
                    <p className="text-xs text-gray-500 mt-1">{v.description}</p>
                )}
            </div>
        );
    };

    const renderStep1 = () => (
        <div>
            <h3 className="text-lg font-semibold mb-4">Select LLM Adapter</h3>
            <p className="text-sm text-gray-500 mb-6">Choose which AI provider to use</p>

            <div className="grid grid-cols-2 gap-3">
                {ADAPTERS.map(adapter => (
                    <button
                        key={adapter.id}
                        onClick={() => setConfig(prev => ({ ...prev, adapter: adapter.id }))}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${config.adapter === adapter.id
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-200 hover:border-gray-300'
                            }`}
                    >
                        <div className="text-2xl mb-2">{adapter.icon}</div>
                        <div className="font-medium text-gray-900">{adapter.name}</div>
                        <div className="text-xs text-gray-500">{adapter.description}</div>
                    </button>
                ))}
            </div>
        </div>
    );

    const renderStep2 = () => {
        const adapterVars = getAdapterEnvVars();
        const requiredVars = adapterVars.filter(v => v.required);
        const optionalVars = adapterVars.filter(v => !v.required);

        return (
            <div>
                <h3 className="text-lg font-semibold mb-2">Configure Environment</h3>
                <p className="text-sm text-gray-500 mb-6">
                    Set up credentials and configuration for {ADAPTERS.find(a => a.id === config.adapter)?.name}
                </p>

                {/* Required Variables */}
                {requiredVars.length > 0 && (
                    <div className="mb-6">
                        <div className="text-sm font-medium text-gray-600 mb-3 flex items-center gap-2">
                            <Key className="w-4 h-4" />
                            Required Credentials
                        </div>
                        {requiredVars.map(v => renderEnvVarInput(v, v.secret))}
                    </div>
                )}

                {/* Optional Variables */}
                {optionalVars.length > 0 && (
                    <div className="mb-6">
                        <div className="text-sm font-medium text-gray-600 mb-3">
                            Optional Settings
                        </div>
                        {optionalVars.map(v => renderEnvVarInput(v, v.secret))}
                    </div>
                )}

                {/* Deployment Settings */}
                <div className="border-t pt-6 mt-6">
                    <div className="text-sm font-medium text-gray-600 mb-3 flex items-center gap-2">
                        <Settings className="w-4 h-4" />
                        Deployment Settings
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm font-medium text-gray-700 block mb-1">
                                Environment Name
                            </label>
                            <input
                                type="text"
                                value={config.environmentName}
                                onChange={(e) => setConfig(prev => ({ ...prev, environmentName: e.target.value }))}
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                placeholder="production"
                            />
                        </div>
                        <div>
                            <label className="text-sm font-medium text-gray-700 block mb-1">
                                Port
                            </label>
                            <input
                                type="number"
                                value={config.port}
                                onChange={(e) => setConfig(prev => ({ ...prev, port: parseInt(e.target.value) || 8080 }))}
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                            />
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const renderStep3 = () => (
        <div>
            <h3 className="text-lg font-semibold mb-2">Review & Deploy</h3>
            <p className="text-sm text-gray-500 mb-6">Review your configuration before deploying</p>

            {/* Summary Card */}
            <div className="bg-gray-50 rounded-xl p-4 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div className="text-gray-500">Agent</div>
                        <div className="font-medium">{agent.name} v{agent.version}</div>
                    </div>
                    <div>
                        <div className="text-gray-500">Adapter</div>
                        <div className="font-medium">{ADAPTERS.find(a => a.id === config.adapter)?.name}</div>
                    </div>
                    <div>
                        <div className="text-gray-500">Environment</div>
                        <div className="font-medium">{config.environmentName}</div>
                    </div>
                    <div>
                        <div className="text-gray-500">Port</div>
                        <div className="font-medium">{config.port}</div>
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-gray-500 text-sm mb-2">Environment Variables</div>
                    <div className="flex flex-wrap gap-2">
                        {Object.keys(config.envVars).filter(k => config.envVars[k]).map(key => (
                            <span
                                key={key}
                                className="inline-flex items-center px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full"
                            >
                                <Check className="w-3 h-3 mr-1" />
                                {key}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Deploy Button */}
            {!deploymentResult && (
                <button
                    onClick={handleDeploy}
                    disabled={deploying || !validateConfig()}
                    className="w-full py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg"
                >
                    {deploying ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Deploying...
                        </>
                    ) : (
                        <>
                            <Rocket className="w-5 h-5" />
                            Deploy Now
                        </>
                    )}
                </button>
            )}

            {/* Deployment Progress */}
            {deploymentResult && (
                <div className="mt-6">
                    <div className="space-y-3">
                        {deploymentResult.steps.map((s, i) => (
                            <div
                                key={i}
                                className={`flex items-center gap-3 p-3 rounded-lg ${s.status === 'completed' ? 'bg-green-50' :
                                    s.status === 'failed' ? 'bg-red-50' :
                                        s.status === 'running' ? 'bg-blue-50' :
                                            'bg-gray-50'
                                    }`}
                            >
                                {s.status === 'completed' && <Check className="w-5 h-5 text-green-600" />}
                                {s.status === 'failed' && <AlertCircle className="w-5 h-5 text-red-600" />}
                                {s.status === 'running' && <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />}
                                {s.status === 'pending' && <div className="w-5 h-5 rounded-full border-2 border-gray-300" />}
                                <div className="flex-1">
                                    <div className="font-medium text-sm capitalize">
                                        {s.step.replace(/_/g, ' ')}
                                    </div>
                                    <div className="text-xs text-gray-500">{s.message}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Success Message */}
                    {deploymentResult.status === 'active' && deploymentResult.container_url && (
                        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-xl">
                            <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
                                <Check className="w-5 h-5" />
                                Deployment Successful!
                            </div>
                            <div className="text-sm text-green-600 mb-3">
                                Your agent is now running and ready to use.
                            </div>
                            <a
                                href={deploymentResult.container_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 text-sm text-green-700 hover:text-green-800 font-medium"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Open Agent: {deploymentResult.container_url}
                            </a>
                        </div>
                    )}

                    {/* Error Message */}
                    {deploymentResult.status === 'failed' && (
                        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                            <div className="flex items-center gap-2 text-red-700 font-medium mb-2">
                                <AlertCircle className="w-5 h-5" />
                                Deployment Failed
                            </div>
                            <div className="text-sm text-red-600">
                                {deploymentResult.error || 'An error occurred during deployment'}
                            </div>
                            <button
                                onClick={() => setDeploymentResult(null)}
                                className="mt-3 text-sm text-red-700 hover:text-red-800 font-medium"
                            >
                                Try Again
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white rounded-2xl p-8 max-w-lg w-full mx-4 text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-green-600 mx-auto mb-4" />
                    <div className="text-gray-600">Loading configuration...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b flex items-center justify-between bg-gradient-to-r from-green-50 to-emerald-50">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <Rocket className="w-5 h-5 text-green-600" />
                            Deploy {agent.name}
                        </h2>
                        <p className="text-sm text-gray-500">Configure and deploy in one click</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Progress Indicator */}
                <div className="px-6 py-4 border-b bg-gray-50">
                    <div className="flex items-center justify-between">
                        {['Adapter', 'Configure', 'Deploy'].map((stepName, i) => (
                            <div key={i} className="flex items-center">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${step > i + 1 ? 'bg-green-500 text-white' :
                                    step === i + 1 ? 'bg-green-100 text-green-700 ring-2 ring-green-500' :
                                        'bg-gray-200 text-gray-400'
                                    }`}>
                                    {step > i + 1 ? <Check className="w-4 h-4" /> : i + 1}
                                </div>
                                <span className={`ml-2 text-sm ${step === i + 1 ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                                    {stepName}
                                </span>
                                {i < 2 && <ChevronRight className="w-5 h-5 text-gray-300 mx-4" />}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {step === 1 && renderStep1()}
                    {step === 2 && renderStep2()}
                    {step === 3 && renderStep3()}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t flex justify-between bg-gray-50">
                    <button
                        onClick={() => step > 1 ? setStep(s => s - 1) : onClose()}
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        {step === 1 ? 'Cancel' : 'Back'}
                    </button>

                    {step < 3 && (
                        <button
                            onClick={() => setStep(s => s + 1)}
                            disabled={step === 2 && !validateConfig()}
                            className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Continue
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    )}

                    {step === 3 && deploymentResult?.status === 'active' && (
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
