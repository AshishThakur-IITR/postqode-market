import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowRight, ShieldCheck, Zap, CheckCircle2, Search, PenTool, Eye } from 'lucide-react';

interface Agent {
    id: string;
    name: string;
    description: string;
    category: string;
    price_cents: number;
    badge: "Capricorn" | "Community";
}

export function HomePage() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchAgents() {
            try {
                const res = await fetch('http://127.0.0.1:8000/api/v1/market/agents');
                if (!res.ok) throw new Error('Failed to fetch agents');
                const data = await res.json();
                setAgents(data);
            } catch (error) {
                console.error("Error fetching agents:", error);
                // Use fallback data
                setAgents([
                    { id: "1", name: "Statement Agent", description: "Reconcile member statements of account with corresponding financial records.", category: "Finance", price_cents: 29900, badge: "Capricorn" },
                    { id: "2", name: "Service Call Agent", description: "AI-powered customer support automation with natural language understanding.", category: "Customer Service", price_cents: 17500, badge: "Capricorn" },
                    { id: "3", name: "Finance Analyzer", description: "Advanced financial analysis and forecasting using machine learning models.", category: "Finance", price_cents: 49900, badge: "Community" },
                ]);
            } finally {
                setLoading(false);
            }
        }
        fetchAgents();
    }, []);

    const formatPrice = (cents: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(cents / 100);
    };

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Hero Section */}
            <section
                className="relative overflow-hidden text-white py-[60px] px-[80px]"
                style={{
                    background: 'linear-gradient(135deg, #052e16 0%, #166534 50%, #15803d 100%)'
                }}
            >
                {/* Abstract Overlays */}
                <div
                    className="absolute inset-0 opacity-50 pointer-events-none"
                    style={{
                        backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255, 255, 255, .03) 35px, rgba(255, 255, 255, .03) 70px), repeating-linear-gradient(-45deg, transparent, transparent 35px, rgba(255, 255, 255, .03) 35px, rgba(255, 255, 255, .03) 70px)`
                    }}
                />
                <div
                    className="absolute top-0 right-0 w-1/2 h-full pointer-events-none"
                    style={{
                        background: 'radial-gradient(circle at 80% 50%, rgba(34, 197, 94, 0.2) 0%, transparent 50%)'
                    }}
                />

                <div className="relative z-10 max-w-[1200px] mx-auto text-center">
                    <h1 className="text-[48px] font-bold mb-5 tracking-tight leading-tight">
                        PostQode Smart Solutions Marketplace
                    </h1>
                    <p className="text-[18px] opacity-95 mb-10 max-w-[800px] mx-auto leading-relaxed">
                        Discover, Collaborate, and Deploy Business-Ready Solutions.
                    </p>

                    <div className="flex justify-center gap-4 mb-[60px]">
                        <Button size="lg" className="bg-white text-green-800 hover:bg-gray-100 font-medium h-[48px] px-8 rounded-lg flex items-center gap-2">
                            <Search className="w-[18px] h-[18px]" />
                            Browse Solutions
                        </Button>
                        <Button size="lg" className="bg-green-500 text-white hover:bg-green-600 font-medium h-[48px] px-8 rounded-lg flex items-center gap-2 border-none">
                            <PenTool className="w-[18px] h-[18px]" />
                            Publish Agent
                        </Button>
                    </div>

                    {/* Hero Features */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-10 text-center">
                        <div className="flex flex-col items-center">
                            <div className="w-12 h-12 mb-4 flex items-center justify-center">
                                <ShieldCheck className="w-8 h-8" />
                            </div>
                            <h3 className="text-[18px] font-semibold mb-2">Community & Secure</h3>
                            <p className="text-[14px] opacity-90">All agents verified and community-approved</p>
                        </div>
                        <div className="flex flex-col items-center">
                            <div className="w-12 h-12 mb-4 flex items-center justify-center">
                                <Zap className="w-8 h-8" />
                            </div>
                            <h3 className="text-[18px] font-semibold mb-2">Ready to Use</h3>
                            <p className="text-[14px] opacity-90">Quick setup and integration</p>
                        </div>
                        <div className="flex flex-col items-center">
                            <div className="w-12 h-12 mb-4 flex items-center justify-center">
                                <CheckCircle2 className="w-8 h-8" />
                            </div>
                            <h3 className="text-[18px] font-semibold mb-2">Trusted Solutions</h3>
                            <p className="text-[14px] opacity-90">Expert-reviewed solutions</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Featured Agents Section */}
            <section className="py-[60px] px-5 bg-gray-50">
                <div className="max-w-[1200px] mx-auto">
                    <div className="flex justify-between items-center mb-8">
                        <div className="flex items-center gap-2 text-green-800">
                            <div className="w-7 h-7 flex items-center justify-center">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                                </svg>
                            </div>
                            <h2 className="text-[28px] font-bold">Featured Agents</h2>
                        </div>
                        <a href="#" className="text-green-600 font-medium text-[14px] hover:underline flex items-center gap-1">
                            View All <ArrowRight className="h-4 w-4" />
                        </a>
                    </div>
                    <p className="text-gray-500 mb-8 -mt-6">Top-rated AI solutions trusted by our member community</p>

                    {loading ? (
                        <div className="text-center py-20 text-gray-500">Loading agents...</div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {agents.map((agent) => {
                                const iconBg = agent.category === 'Finance' ? 'bg-green-500' : 'bg-emerald-500';

                                return (
                                    <div key={agent.id} className="bg-white rounded-xl p-6 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col h-full border border-transparent">
                                        <div className="flex gap-4 mb-3 items-start">
                                            <div className={`w-12 h-12 rounded-xl ${iconBg} text-white flex items-center justify-center font-bold text-lg flex-shrink-0`}>
                                                {agent.name.substring(0, 2).toUpperCase()}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h3 className="text-[16px] font-semibold mb-1 truncate text-gray-900">{agent.name}</h3>
                                                <p className="text-[13px] text-gray-500">PostQode</p>
                                            </div>
                                            <span className={`px-2.5 py-1 rounded text-[11px] font-semibold text-white ${agent.badge === 'Capricorn' ? 'bg-green-800' : 'bg-green-500'}`}>
                                                {agent.badge}
                                            </span>
                                        </div>

                                        <div className="mb-auto">
                                            <span className="inline-block px-3 py-1 bg-green-100 rounded-md text-[12px] text-green-800 mb-3">
                                                {agent.category}
                                            </span>
                                            <p className="text-[14px] text-gray-500 leading-relaxed line-clamp-3">
                                                {agent.description}
                                            </p>
                                        </div>

                                        <div className="flex items-center justify-between mt-6 pt-4">
                                            <span className="text-[24px] font-bold text-green-800">
                                                {formatPrice(agent.price_cents)}
                                            </span>
                                            <div className="flex gap-2">
                                                <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 hover:bg-gray-50 bg-white">
                                                    <Eye className="w-4 h-4 text-gray-600" />
                                                </button>
                                                <button className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium text-[14px] transition-colors">
                                                    Get it Now
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
}
