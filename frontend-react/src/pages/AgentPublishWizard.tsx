import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    Upload, Package, Check, ChevronRight, ChevronLeft,
    Eye, Send, AlertCircle, FileArchive, Info, DollarSign
} from 'lucide-react';

interface ExtractedManifest {
    name: string;
    description: string;
    version: string;
    category: string;
    inputs: any[];
    outputs: any[];
}

interface UploadResult {
    agent: {
        id: string;
        name: string;
        description: string;
        category: string;
        version: string;
        price_cents: number;
        status: string;
        package_url: string;
        package_size_bytes: number;
    };
    extracted_from_manifest: ExtractedManifest;
    validation_warnings: string[];
    is_update: boolean;
    was_published?: boolean;
    message?: string;
}

export function AgentPublishWizard() {
    const navigate = useNavigate();
    const { user } = useAuth();

    const [step, setStep] = useState(1);
    const [dragActive, setDragActive] = useState(false);

    // File state
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

    // Price (only thing user sets - not in manifest)
    const [priceDollars, setPriceDollars] = useState<string>('');

    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

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
            handleFileSelect(e.dataTransfer.files[0]);
        }
    }, []);

    const handleFileSelect = (selectedFile: File) => {
        if (!selectedFile.name.endsWith('.zip')) {
            setError('Please upload a .zip file containing agent.yaml');
            return;
        }
        setFile(selectedFile);
        setError('');
        setUploadResult(null);
    };

    const handleUploadPackage = async () => {
        if (!file || !user?.id) return;

        setUploading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const priceCents = Math.round(parseFloat(priceDollars || '0') * 100);

            const response = await fetch(
                `/api/v1/market/publish-from-package?publisher_id=${user.id}&price_cents=${priceCents}`,
                { method: 'POST', body: formData }
            );

            if (!response.ok) {
                const err = await response.json();
                if (err.detail?.errors) {
                    throw new Error(err.detail.errors.join(', '));
                }
                throw new Error(err.detail?.message || err.detail || 'Upload failed');
            }

            const result: UploadResult = await response.json();
            setUploadResult(result);
            setStep(2);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    const handleSubmitForReview = async () => {
        if (!uploadResult?.agent.id || !user?.id) return;

        // If agent was already published, no need to submit for review
        // Just navigate back - the version update is already applied
        if (uploadResult.was_published) {
            navigate('/publisher');
            return;
        }

        setIsSubmitting(true);
        try {
            const response = await fetch(
                `/api/v1/market/agents/${uploadResult.agent.id}/submit?publisher_id=${user.id}`,
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

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
    };

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Publish Agent</h1>
                <p className="text-gray-500 mt-1">Upload your agent package to publish to the marketplace</p>
            </div>

            {/* Step Indicator */}
            <div className="flex items-center mb-8 bg-white rounded-xl p-4 border">
                {['Upload Package', 'Review & Submit'].map((stepName, i) => (
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
                        {i < 1 && <ChevronRight className="w-5 h-5 text-gray-300 mx-4 flex-shrink-0" />}
                    </div>
                ))}
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span>{error}</span>
                </div>
            )}

            {/* Step 1: Upload Package */}
            {step === 1 && (
                <div className="space-y-6">
                    {/* Info Banner */}
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
                        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-blue-800">
                            <strong>Package-First Publishing:</strong> Your agent's name, description, version, and category
                            are automatically extracted from the <code className="bg-blue-100 px-1 rounded">agent.yaml</code> manifest
                            in your package. You only need to set the price.
                        </div>
                    </div>

                    {/* Price Input */}
                    <div className="bg-white rounded-xl p-6 border">
                        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                            <DollarSign className="w-4 h-4" />
                            Listing Price (USD)
                        </label>
                        <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={priceDollars}
                            onChange={(e) => setPriceDollars(e.target.value)}
                            className="w-full max-w-xs px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                            placeholder="29.99"
                        />
                        <p className="text-xs text-gray-500 mt-2">Set to 0 for a free agent</p>
                    </div>

                    {/* Upload Area */}
                    <div className="bg-white rounded-xl p-6 border">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Package className="w-5 h-5" />
                            Agent Package
                        </h2>

                        <div
                            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${dragActive ? 'border-green-500 bg-green-50' :
                                file ? 'border-green-300 bg-green-50' :
                                    'border-gray-300 hover:border-gray-400'
                                }`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <input
                                type="file"
                                accept=".zip"
                                onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
                                className="hidden"
                                id="file-upload"
                            />
                            <label htmlFor="file-upload" className="cursor-pointer">
                                {file ? (
                                    <>
                                        <FileArchive className="w-12 h-12 text-green-500 mx-auto mb-4" />
                                        <p className="text-lg font-medium text-gray-900">{file.name}</p>
                                        <p className="text-sm text-gray-500 mt-1">{formatBytes(file.size)}</p>
                                        <p className="text-xs text-green-600 mt-2">Click or drop to replace</p>
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                                        <p className="text-lg font-medium text-gray-700">
                                            Drop your package here or click to browse
                                        </p>
                                        <p className="text-sm text-gray-500 mt-1">
                                            ZIP file containing agent.yaml
                                        </p>
                                    </>
                                )}
                            </label>
                        </div>

                        {file && (
                            <button
                                onClick={handleUploadPackage}
                                disabled={uploading}
                                className="mt-6 w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {uploading ? (
                                    <>
                                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                        Validating & Uploading...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-5 h-5" />
                                        Upload & Extract Metadata
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Step 2: Review & Submit */}
            {step === 2 && uploadResult && (
                <div className="space-y-6">
                    {/* Success Banner */}
                    <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex gap-3">
                        <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-green-800">
                            <strong>Package uploaded successfully!</strong>
                            {uploadResult.is_update && ' This is an update to an existing agent.'}
                        </div>
                    </div>

                    {/* Warnings */}
                    {uploadResult.validation_warnings.length > 0 && (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                            <div className="flex gap-2 mb-2">
                                <AlertCircle className="w-5 h-5 text-yellow-600" />
                                <span className="font-medium text-yellow-800">Warnings</span>
                            </div>
                            <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                                {uploadResult.validation_warnings.map((w, i) => <li key={i}>{w}</li>)}
                            </ul>
                        </div>
                    )}

                    {/* Extracted Info */}
                    <div className="bg-white rounded-xl p-6 border">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Eye className="w-5 h-5" />
                            Extracted from Package
                        </h2>

                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs text-gray-500 uppercase tracking-wide">Name</label>
                                    <p className="text-lg font-medium text-gray-900">{uploadResult.agent.name}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase tracking-wide">Version</label>
                                    <p className="text-lg font-medium text-gray-900">{uploadResult.agent.version}</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs text-gray-500 uppercase tracking-wide">Category</label>
                                    <span className="inline-block mt-1 bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm">
                                        {uploadResult.agent.category}
                                    </span>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase tracking-wide">Price</label>
                                    <p className="text-lg font-medium text-gray-900">
                                        {uploadResult.agent.price_cents === 0
                                            ? 'Free'
                                            : `$${(uploadResult.agent.price_cents / 100).toFixed(2)}`}
                                    </p>
                                </div>
                            </div>

                            <div>
                                <label className="text-xs text-gray-500 uppercase tracking-wide">Description</label>
                                <p className="text-gray-700 mt-1 whitespace-pre-line">
                                    {uploadResult.agent.description}
                                </p>
                            </div>

                            <div className="pt-4 border-t grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-500">Package Size:</span>
                                    <span className="ml-2 font-medium">{formatBytes(uploadResult.agent.package_size_bytes)}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">Inputs:</span>
                                    <span className="ml-2 font-medium">{uploadResult.extracted_from_manifest.inputs.length}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">Outputs:</span>
                                    <span className="ml-2 font-medium">{uploadResult.extracted_from_manifest.outputs.length}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Submit/Done Button */}
                    <button
                        onClick={handleSubmitForReview}
                        disabled={isSubmitting}
                        className="w-full py-4 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2 text-lg"
                    >
                        {isSubmitting ? (
                            <>
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                Submitting...
                            </>
                        ) : uploadResult.was_published ? (
                            <>
                                <Check className="w-5 h-5" />
                                Done - Version Updated
                            </>
                        ) : (
                            <>
                                <Send className="w-5 h-5" />
                                Submit for Review
                            </>
                        )}
                    </button>

                    <p className="text-center text-sm text-gray-500">
                        {uploadResult.was_published
                            ? 'Your agent version has been updated. Users will see the new version immediately.'
                            : 'Your agent will be reviewed by our team before being published to the marketplace.'
                        }
                    </p>
                </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <button
                    onClick={() => step > 1 ? setStep(s => s - 1) : navigate('/publisher')}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900"
                >
                    <ChevronLeft className="w-5 h-5" />
                    {step === 1 ? 'Cancel' : 'Back'}
                </button>
            </div>
        </div>
    );
}
