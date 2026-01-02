import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

const API_BASE = 'http://localhost:8000/api/v1';

interface User {
    id: string;
    email: string;
    name: string | null;
    organization_id: string | null;
    role: string;
    is_active: boolean;
    is_verified: boolean;
    is_marketplace_owner: boolean;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, name?: string, organization_name?: string) => Promise<void>;
    logout: () => void;
    error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Check for existing token on mount
    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (token) {
            fetchCurrentUser(token);
        } else {
            setIsLoading(false);
        }
    }, []);

    const fetchCurrentUser = async (token: string) => {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                // Token invalid, clear it
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
            }
        } catch (err) {
            console.error('Failed to fetch user:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const login = async (email: string, password: string) => {
        setError(null);
        setIsLoading(true);

        try {
            // Use OAuth2 form data format
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Login failed');
            }

            const tokens = await response.json();
            localStorage.setItem('access_token', tokens.access_token);
            localStorage.setItem('refresh_token', tokens.refresh_token);

            await fetchCurrentUser(tokens.access_token);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
            setIsLoading(false);
            throw err;
        }
    };

    const register = async (email: string, password: string, name?: string, organization_name?: string) => {
        setError(null);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email,
                    password,
                    name,
                    organization_name,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Registration failed');
            }

            // Auto-login after registration
            await login(email, password);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
            setIsLoading(false);
            throw err;
        }
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                register,
                logout,
                error,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
