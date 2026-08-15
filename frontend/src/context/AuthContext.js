import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [loading, setLoading] = useState(true);

    const api = useCallback(() => {
        const instance = axios.create({
            baseURL: API,
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        return instance;
    }, [token]);

    useEffect(() => {
        const fetchUser = async () => {
            if (token) {
                try {
                    const res = await api().get('/auth/me');
                    setUser(res.data);
                } catch (err) {
                    console.error('Auth check failed:', err);
                    logout();
                }
            }
            setLoading(false);
        };
        fetchUser();
    }, [token, api]);

    const login = async (email, password) => {
        const res = await api().post('/auth/login', { email, password });
        localStorage.setItem('token', res.data.token);
        setToken(res.data.token);
        setUser(res.data.user);
        return res.data.user;
    };

    const register = async (name, email, password, role = 'viewer') => {
        const res = await api().post('/auth/register', { name, email, password, role });
        localStorage.setItem('token', res.data.token);
        setToken(res.data.token);
        setUser(res.data.user);
        return res.data.user;
    };

    const logout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
    };

    const hasRole = (roles) => {
        if (!user) return false;
        if (typeof roles === 'string') return user.role === roles;
        return roles.includes(user.role);
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, login, register, logout, api, hasRole }}>
            {children}
        </AuthContext.Provider>
    );
};

export default AuthContext;
