import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    Upload, Package, Check, X, ChevronRight, ChevronLeft,
    Eye, Send, AlertCircle
} from 'lucide-react';

interface FormData {
    name: string;
    description: string;
    category: string;
    price_cents: number;
    version: string;
}

interface ValidationResult {
    is_valid: boolean;
    manifest: any;
    errors: string[];
    warnings: string[];
}

const CATEGORIES = [
    'Data Analytics', 'Finance', 'Procurement', 'Service Operations',
    'Customer Service', 'Marketing', 'HR', 'Other'
];

export function AgentPublishWizard() {
    const navigate = useNavigate();
    const { user } = useAuth();

    const [step, setStep] = useState(1);
    const [agentId, setAgentId] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);

    const [formData, setFormData] = useState<FormData>({
        name: '',
        description: '',
        category: 'Data Analytics',
        price_cents: 0,
        version: '1.0.0'
    });

    const [file, setFile] = useState<File | null>(null);
    const [validation, setValidation] = useState<ValidationResult | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadComplete, setUploadComplete] = useState(false);

    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleCreateAgent = async () => {
        if (!user?.id) return;
        setIsSubmitting(true);
        setError('');

        try {
            const response = await fetch(`/api/v1/market/agents?publisher_id=${user.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to create agent');
            }

            const agent = await response.json();
            setAgentId(agent.id);
            setStep(2);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    }, []);

    const handleFile = async (selectedFile: File) => {
        if (!selectedFile.name.endsWith('.zip')) {
            setError('Please upload a .zip file');
            return;
        }
        setFile(selectedFile);
        setError('');

        const formDataUpload = new FormData();
        formDataUpload.append('file', selectedFile);

        try {
            const response = await fetch(`/api/v1/market/agents/${agentId}/validate-package`, {
                method: 'POST',
                body: formDataUpload
            });
            const result = await response.json();
            setValidation(result);
        } catch (err) {
            console.error('Validation failed:', err);
        }
    };

    const handleUploadPackage = async () => {
        if (!file || !agentId || !user?.id) return;

        setUploading(true);
        setError('');

        try {
            const formDataUpload = new FormData();
            formDataUpload.append('file', file);

            const response = await fetch(
                `/api/v1/market/agents/${agentId}/upload?publisher_id=${user.id}`,
                { method: 'POST', body: formDataUpload }
            );

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail?.message || 'Upload failed');
            }

            setUploadComplete(true);
            setStep(3);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    const handleSubmitForReview = async () => {
        if (!agentId || !user?.id) return;

        setIsSubmitting(true);
        try {
            const response = await fetch(
                `/api/v1/market/agents/${agentId}/submit?publisher_id=${user.id}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ notes: '' })
                }
            );

            if (!response.ok) throw new Error('Failed to submit');
            navigate('/publisher');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Publish New Agent</h1>
                <p className="text-gray-500 mt-1">Create, upload, and submit your agent package</p>
            </div>

            <div className="flex items-center mb-8 bg-white rounded-xl p-4 border">
                {['Agent Details', 'Upload Package', 'Review & Submit'].map((stepName, i) => (
                    <div key={i} className="flex items-center flex-1">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${step > i + 1 ? 'bg-green-500 text-white' :
                                step === i + 1 ? 'bg-green-100 text-green-700 border-2 border-green-500' :
                                    'bg-gray-100 text-gray-400'
                            }`}>
                            {step > i + 1 ? <Check className="w-5 h-5" /> : i + 1}
                        </div>
                        <span className={`ml-3 text-sm ${step === i + 1 ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                            {stepName}
                        </span>
                        {i < 2 && <ChevronRight className="w-5 h-5 text-gray-300 mx-4 flex-shrink-0" />}
                    </div>
                ))}
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-5 h-5" />
                    {error}
                </div>
            )}

            {step === 1 && (
                <div className="bg-white rounded-xl p-6 border">
                    <h2 className="text-xl font-semibold mb-6">Agent Details</h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name *</label>
                            <input
                                type="text"
                                required
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500"
                                placeholder="e.g., Invoice Processor"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
                            <textarea
                                required
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500"
                                placeholder="Describe what your agent does..."
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                <select
                                    value={formData.category}
                                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-lg"
                                >
                                    {CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Price (USD)</label>
                                <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={formData.price_cents / 100 || ''}
                                    onChange={(e) => {
                                        const val = parseFloat(e.target.value);
                                        setFormData({ ...formData, price_cents: isNaN(val) ? 0 : Math.round(val * 100) });
                                    }}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-lg"
                                    placeholder="29.99"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                            <input
                                type="text"
                                value={formData.version}
                                onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                                className="w-full px-4 py-3 border border-gray-200 rounded-lg"
                            />
                        </div>
                    </div>
                </div>
            )}

            {step === 2 && (
                <div className="bg-white rounded-xl p-6 border">
                    <h2 className="text-xl font-semibold mb-2">Upload Package</h2>
                    <p className="text-gray-500 mb-6">Upload your agent package (.zip) containing agent.yaml</p>

                    <div
                        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${dragActive ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-gray-400'
                            }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                    >
                        <input
                            type="file"
                            accept=".zip"
                            onChange={(e) => e.target.files && handleFile(e.target.files[0])}
                            className="hidden"
                            id="file-upload"
                        />
                        <label htmlFor="file-upload" className="cursor-pointer">
                            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-lg font-medium text-gray-700">
                                {file ? file.name : 'Drop your package here or click to browse'}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                                {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'Only .zip files'}
                            </p>
                        </label>
                    </div>

                    {validation && (
                        <div className={`mt-6 p-4 rounded-lg ${validation.is_valid ? 'bg-green-50' : 'bg-red-50'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                {validation.is_valid ? (
                                    <><Check className="w-5 h-5 text-green-600" /><span className="font-medium text-green-700">Package Valid</span></>
                                ) : (
                                    <><X className="w-5 h-5 text-red-600" /><span className="font-medium text-red-700">Validation Failed</span></>
                                )}
                            </div>
                            {validation.errors.length > 0 && (
                                <ul className="list-disc list-inside text-sm text-red-600">
                                    {validation.errors.map((e, i) => <li key={i}>{e}</li>)}
                                </ul>
                            )}
                        </div>
                    )}

                    {file && (
                        <button
                            onClick={handleUploadPackage}
                            disabled={uploading}
                            className="mt-6 w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                            {uploading ? 'Uploading...' : <><Package className="w-5 h-5" /> Upload Package</>}
                        </button>
                    )}
                </div>
            )}

            {step === 3 && (
                <div className="bg-white rounded-xl p-6 border">
                    <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <Eye className="w-6 h-6" /> Review & Submit
                    </h2>

                    <div className="space-y-4 mb-6">
                        <div className="p-4 bg-gray-50 rounded-lg">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div><span className="text-gray-500">Name:</span> <strong>{formData.name}</strong></div>
                                <div><span className="text-gray-500">Category:</span> <strong>{formData.category}</strong></div>
                                <div><span className="text-gray-500">Version:</span> <strong>{formData.version}</strong></div>
                                <div><span className="text-gray-500">Price:</span> <strong>${(formData.price_cents / 100).toFixed(2)}</strong></div>
                            </div>
                            <div className="mt-3 text-sm">
                                <span className="text-gray-500">Description:</span>
                                <p className="mt-1">{formData.description}</p>
                            </div>
                        </div>

                        {uploadComplete && (
                            <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg text-green-700">
                                <Check className="w-5 h-5" />
                                <span>Package uploaded successfully</span>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleSubmitForReview}
                        disabled={isSubmitting}
                        className="w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {isSubmitting ? 'Submitting...' : <><Send className="w-5 h-5" /> Submit for Review</>}
                    </button>

                    <p className="text-center text-sm text-gray-500 mt-4">
                        Your agent will be reviewed before publishing.
                    </p>
                </div>
            )}

            <div className="flex justify-between mt-6">
                <button
                    onClick={() => step > 1 ? setStep(s => s - 1) : navigate('/publisher')}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
                >
                    <ChevronLeft className="w-5 h-5" />
                    {step === 1 ? 'Cancel' : 'Back'}
                </button>

                {step === 1 && (
                    <button
                        onClick={handleCreateAgent}
                        disabled={!formData.name || !formData.description || isSubmitting}
                        className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                        {isSubmitting ? 'Creating...' : 'Continue'}
                        <ChevronRight className="w-5 h-5" />
                    </button>
                )}
            </div>
        </div>
    );
}
