import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2, Building, CheckCircle } from 'lucide-react';

export function OrgRegistrationPage() {
    const navigate = useNavigate();
    const { login } = useAuth(); // We'll manually call registration API then login
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        orgName: '',
        adminName: '',
        email: '',
        password: '',
        plan: 'STARTER'
    });

    const PLANS = [
        { id: 'STARTER', name: 'Starter', price: '$49/mo' },
        { id: 'PROFESSIONAL', name: 'Professional', price: '$149/mo' },
        { id: 'ENTERPRISE', name: 'Enterprise', price: 'Custom' },
    ];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            // Register Organization
            const response = await fetch('/api/v1/organizations/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.orgName,
                    slug: formData.orgName.toLowerCase().replace(/[^a-z0-9]/g, '-'),
                    subscription_plan: formData.plan,
                    owner_email: formData.email, // backend expects these in query or body? 
                    // Wait, create_organization takes org_data (body) and owner_email, owner_name (query)
                    // Let me check the backend signature again.
                })
            });

            // Re-checking backend signature:
            // def create_organization(org_data: OrganizationCreate, owner_email: str, owner_name: str ...)
            // These are query params by default in FastAPI if not part of Pydantic model.
            // I should construct the URL with query params.

            const url = `/api/v1/organizations/?owner_email=${encodeURIComponent(formData.email)}&owner_name=${encodeURIComponent(formData.adminName)}`;

            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.orgName,
                    slug: formData.orgName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
                    subscription_plan: formData.plan
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Registration failed');
            }

            // Auto-login
            await login(formData.email, formData.password);

            // Redirect
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
            <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden flex flex-col md:flex-row">

                {/* Left Side - Info */}
                <div className="bg-slate-900 text-white p-8 md:w-1/3 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-6">
                            <Building className="w-8 h-8 text-green-400" />
                            <span className="font-bold text-xl">PostQode</span>
                        </div>
                        <h2 className="text-2xl font-bold mb-4">Create your Organization</h2>
                        <ul className="space-y-3 text-gray-300 text-sm">
                            <li className="flex items-start gap-2">
                                <CheckCircle className="w-4 h-4 text-green-400 mt-1" />
                                <span>Manage teams and members</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle className="w-4 h-4 text-green-400 mt-1" />
                                <span>Publish and distribute agents</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle className="w-4 h-4 text-green-400 mt-1" />
                                <span>Enterprise-grade security</span>
                            </li>
                        </ul>
                    </div>
                    <div className="text-xs text-gray-500 mt-8">
                        © 2024 PostQode Inc.
                    </div>
                </div>

                {/* Right Side - Form */}
                <div className="p-8 md:w-2/3">
                    <h3 className="text-xl font-bold text-gray-900 mb-6">Organization Details</h3>

                    {error && (
                        <div className="mb-6 bg-red-50 text-red-700 p-3 rounded-lg text-sm border border-red-200">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                                    value={formData.orgName}
                                    onChange={e => setFormData({ ...formData, orgName: e.target.value })}
                                    placeholder="Acme Corp"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Select Plan</label>
                                <select
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                                    value={formData.plan}
                                    onChange={e => setFormData({ ...formData, plan: e.target.value })}
                                >
                                    {PLANS.map(p => (
                                        <option key={p.id} value={p.id}>{p.name} ({p.price})</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Admin Name</label>
                            <input
                                type="text"
                                required
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                                value={formData.adminName}
                                onChange={e => setFormData({ ...formData, adminName: e.target.value })}
                                placeholder="John Doe"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Work Email</label>
                            <input
                                type="email"
                                required
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                                value={formData.email}
                                onChange={e => setFormData({ ...formData, email: e.target.value })}
                                placeholder="admin@acme.com"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                            <input
                                type="password"
                                required
                                minLength={8}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                                value={formData.password}
                                onChange={e => setFormData({ ...formData, password: e.target.value })}
                                placeholder="••••••••"
                            />
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                            >
                                {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                                Create Organization
                            </button>
                        </div>

                        <div className="text-center text-sm text-gray-500 mt-4">
                            Already have an account? <a href="/login" className="text-green-600 hover:underline">Sign in</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

