import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FlaskConical, Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const LoginPage = () => {
    const { login, register, user, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [form, setForm] = useState({
        name: '',
        email: '',
        password: '',
        role: 'viewer'
    });

    // Redirect if already logged in
    useEffect(() => {
        if (user && !authLoading) {
            navigate('/dashboard', { replace: true });
        }
    }, [user, authLoading, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            if (isLogin) {
                await login(form.email, form.password);
                toast.success('Welcome back!');
                navigate('/dashboard', { replace: true });
            } else {
                await register(form.name, form.email, form.password, form.role);
                toast.success('Account created successfully!');
                navigate('/dashboard', { replace: true });
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Authentication failed');
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex" data-testid="login-page">
            {/* Left side - Hero Image */}
            <div className="hidden lg:flex lg:w-1/2 relative bg-slate-900">
                <img 
                    src="https://images.pexels.com/photos/8439003/pexels-photo-8439003.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                    alt="Laboratory"
                    className="w-full h-full object-cover opacity-60"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/50 to-transparent" />
                <div className="absolute bottom-0 left-0 p-12">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 bg-white rounded-sm flex items-center justify-center">
                            <FlaskConical className="w-7 h-7 text-slate-900" />
                        </div>
                        <div>
                            <h1 className="text-white font-heading text-2xl font-bold tracking-tight">COSMETIC</h1>
                            <p className="text-white/60 text-xs tracking-widest">INVENTORY SYSTEM</p>
                        </div>
                    </div>
                    <p className="text-white/80 text-lg max-w-md leading-relaxed">
                        Stage-wise inventory management for cosmetic manufacturing. Track raw materials, production, packaging, and dispatch.
                    </p>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
                <div className="w-full max-w-md">
                    {/* Mobile logo */}
                    <div className="lg:hidden flex items-center gap-3 mb-8">
                        <div className="w-10 h-10 bg-slate-900 rounded-sm flex items-center justify-center">
                            <FlaskConical className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-slate-900 font-heading text-xl font-bold tracking-tight">COSMETIC</h1>
                            <p className="text-slate-500 text-xs tracking-widest">INVENTORY SYSTEM</p>
                        </div>
                    </div>

                    <div className="bg-white p-8 rounded-sm shadow-sm border border-slate-200">
                        <h2 className="font-heading text-2xl font-bold text-slate-900 mb-2">
                            {isLogin ? 'Welcome Back' : 'Create Account'}
                        </h2>
                        <p className="text-slate-500 text-sm mb-8">
                            {isLogin ? 'Enter your credentials to access the system' : 'Register to get started'}
                        </p>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            {!isLogin && (
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                        Full Name
                                    </label>
                                    <input
                                        type="text"
                                        data-testid="name-input"
                                        className="input-default"
                                        placeholder="John Doe"
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                        required={!isLogin}
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    data-testid="email-input"
                                    className="input-default"
                                    placeholder="you@company.com"
                                    value={form.email}
                                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                    Password
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        data-testid="password-input"
                                        className="input-default pr-10"
                                        placeholder="Enter password"
                                        value={form.password}
                                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>

                            {!isLogin && (
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                        Role
                                    </label>
                                    <select
                                        data-testid="role-select"
                                        className="input-default"
                                        value={form.role}
                                        onChange={(e) => setForm({ ...form, role: e.target.value })}
                                    >
                                        <option value="viewer">Viewer</option>
                                        <option value="store_keeper">Store Keeper</option>
                                        <option value="production_manager">Production Manager</option>
                                    </select>
                                </div>
                            )}

                            <button
                                type="submit"
                                data-testid="submit-btn"
                                disabled={loading}
                                className="w-full btn-primary flex items-center justify-center gap-2"
                            >
                                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                                {isLogin ? 'Sign In' : 'Create Account'}
                            </button>
                        </form>

                        <div className="mt-6 text-center">
                            <button
                                onClick={() => setIsLogin(!isLogin)}
                                data-testid="toggle-auth-mode"
                                className="text-sm text-slate-600 hover:text-slate-900"
                            >
                                {isLogin ? "Don't have an account? " : 'Already have an account? '}
                                <span className="font-semibold">{isLogin ? 'Register' : 'Sign In'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
