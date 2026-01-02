import { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PLANS = [
    {
        id: 'STARTER',
        name: 'Starter',
        price: '49',
        features: ['Up to 5 Agents', 'Basic Analytics', 'Community Support', 'Standard API Rate Limits'],
        recommended: false
    },
    {
        id: 'PROFESSIONAL',
        name: 'Professional',
        price: '149',
        features: ['Up to 20 Agents', 'Advanced Analytics', 'Priority Support', 'Higher API Rate Limits', 'Custom Branding'],
        recommended: true
    },
    {
        id: 'ENTERPRISE',
        name: 'Enterprise',
        price: 'Custom',
        features: ['Unlimited Agents', 'Dedicated Success Manager', '24/7 Phone Support', 'Custom Contracts', 'SSO Integration'],
        recommended: false
    }
];

export function SubscriptionPage() {
    const { user } = useAuth();
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
    const [loading, setLoading] = useState<string | null>(null);

    const handleSubscribe = async (planId: string) => {
        setLoading(planId);
        // TODO: Implement actual Stripe subscription or backend call
        setTimeout(() => {
            alert(`Subscribed to ${planId}`);
            setLoading(null);
        }, 1500);
    };

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            <div className="text-center mb-12">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">Simple, Transparent Pricing</h1>
                <p className="text-xl text-gray-500">Choose the plan that's right for your organization</p>

                <div className="mt-8 inline-flex bg-gray-100 rounded-lg p-1">
                    <button
                        onClick={() => setBillingCycle('monthly')}
                        className={`px-6 py-2 rounded-md text-sm font-medium transition-all ${billingCycle === 'monthly' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'
                            }`}
                    >
                        Monthly
                    </button>
                    <button
                        onClick={() => setBillingCycle('yearly')}
                        className={`px-6 py-2 rounded-md text-sm font-medium transition-all ${billingCycle === 'yearly' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'
                            }`}
                    >
                        Yearly <span className="text-green-600 text-xs ml-1">-20%</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {PLANS.map((plan) => (
                    <div key={plan.id} className={`relative bg-white rounded-2xl shadow-sm border ${plan.recommended ? 'border-green-500 ring-2 ring-green-500 ring-opacity-20' : 'border-gray-200'} p-8 flex flex-col`}>
                        {plan.recommended && (
                            <div className="absolute top-0 right-0 transform translate-x-2 -translate-y-2">
                                <span className="bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</span>
                            </div>
                        )}

                        <div className="mb-8">
                            <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                            <div className="mt-4 flex items-baseline">
                                <span className="text-4xl font-bold text-gray-900">
                                    {plan.price === 'Custom' ? 'Custom' : `$${plan.price}`}
                                </span>
                                {plan.price !== 'Custom' && (
                                    <span className="ml-2 text-gray-500">/{billingCycle === 'monthly' ? 'mo' : 'yr'}</span>
                                )}
                            </div>
                        </div>

                        <ul className="space-y-4 mb-8 flex-1">
                            {plan.features.map((feature, idx) => (
                                <li key={idx} className="flex items-start gap-3">
                                    <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                                    <span className="text-gray-600 text-sm">{feature}</span>
                                </li>
                            ))}
                        </ul>

                        <button
                            onClick={() => handleSubscribe(plan.id)}
                            disabled={!!loading}
                            className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 ${plan.recommended
                                    ? 'bg-green-600 text-white hover:bg-green-700'
                                    : 'bg-gray-50 text-gray-900 hover:bg-gray-100'
                                }`}
                        >
                            {loading === plan.id && <Loader2 className="w-4 h-4 animate-spin" />}
                            {plan.price === 'Custom' ? 'Contact Sales' : 'Get Started'}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
