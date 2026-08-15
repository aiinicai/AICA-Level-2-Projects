import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Edit2, X, Loader2, UserCheck, UserX } from 'lucide-react';
import { toast } from 'sonner';

const UsersPage = () => {
    const { api, user: currentUser } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: '',
        email: '',
        password: '',
        role: 'viewer',
        is_active: true
    });

    const fetchUsers = useCallback(async () => {
        try {
            const res = await api().get('/users');
            setUsers(res.data);
        } catch (err) {
            toast.error('Failed to fetch users');
        }
        setLoading(false);
    }, [api]);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (editingUser) {
                const updateData = { ...form };
                if (!updateData.password) delete updateData.password;
                await api().put(`/users/${editingUser.id}`, updateData);
                toast.success('User updated');
            } else {
                await api().post('/auth/register', form);
                toast.success('User created');
            }
            setShowModal(false);
            setEditingUser(null);
            resetForm();
            fetchUsers();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleToggleStatus = async (userId, currentStatus) => {
        try {
            await api().put(`/users/${userId}`, { is_active: !currentStatus });
            toast.success(`User ${!currentStatus ? 'activated' : 'deactivated'}`);
            fetchUsers();
        } catch (err) {
            toast.error('Failed to update user status');
        }
    };

    const openEdit = (user) => {
        setEditingUser(user);
        setForm({
            name: user.name,
            email: user.email,
            password: '',
            role: user.role,
            is_active: user.is_active
        });
        setShowModal(true);
    };

    const resetForm = () => {
        setForm({ name: '', email: '', password: '', role: 'viewer', is_active: true });
    };

    const getRoleBadge = (role) => {
        const badges = {
            admin: 'bg-red-100 text-red-700',
            production_manager: 'bg-blue-100 text-blue-700',
            store_keeper: 'bg-amber-100 text-amber-700',
            viewer: 'bg-slate-100 text-slate-600'
        };
        return badges[role] || 'bg-slate-100 text-slate-600';
    };

    const filteredUsers = users.filter(u => 
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6" data-testid="users-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">USER MANAGEMENT</h1>
                    <p className="text-slate-500 text-sm mt-1">Manage system users and permissions</p>
                </div>
                <button 
                    onClick={() => { setShowModal(true); setEditingUser(null); resetForm(); }}
                    className="btn-primary flex items-center gap-2"
                    data-testid="add-user-btn"
                >
                    <Plus size={16} /> Add User
                </button>
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search users..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-users"
                />
            </div>

            {/* Table */}
            <div className="card-default overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredUsers.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">No users found.</div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.map((user) => (
                                <tr key={user.id} data-testid={`user-row-${user.id}`}>
                                    <td className="font-medium text-slate-900">{user.name}</td>
                                    <td className="text-slate-600">{user.email}</td>
                                    <td>
                                        <span className={`status-badge ${getRoleBadge(user.role)}`}>
                                            {user.role.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`flex items-center gap-1 text-sm ${user.is_active ? 'text-green-600' : 'text-red-600'}`}>
                                            {user.is_active ? <UserCheck size={14} /> : <UserX size={14} />}
                                            {user.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <button 
                                                onClick={() => openEdit(user)}
                                                className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                data-testid={`edit-user-${user.id}`}
                                            >
                                                <Edit2 size={16} />
                                            </button>
                                            {user.id !== currentUser?.id && (
                                                <button 
                                                    onClick={() => handleToggleStatus(user.id, user.is_active)}
                                                    className={`p-2 transition-colors ${user.is_active ? 'text-slate-400 hover:text-red-600' : 'text-slate-400 hover:text-green-600'}`}
                                                    title={user.is_active ? 'Deactivate' : 'Activate'}
                                                    data-testid={`toggle-user-${user.id}`}
                                                >
                                                    {user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="user-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">
                                {editingUser ? 'Edit User' : 'Add User'}
                            </h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Full Name</label>
                                <input
                                    type="text"
                                    className="input-default"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    required
                                    data-testid="user-name-input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Email</label>
                                <input
                                    type="email"
                                    className="input-default"
                                    value={form.email}
                                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                                    required
                                    disabled={!!editingUser}
                                    data-testid="user-email-input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                    Password {editingUser && <span className="text-slate-400 normal-case">(leave blank to keep current)</span>}
                                </label>
                                <input
                                    type="password"
                                    className="input-default"
                                    value={form.password}
                                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                                    required={!editingUser}
                                    data-testid="user-password-input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Role</label>
                                <select
                                    className="input-default"
                                    value={form.role}
                                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                                    data-testid="user-role-select"
                                >
                                    <option value="viewer">Viewer</option>
                                    <option value="store_keeper">Store Keeper</option>
                                    <option value="production_manager">Production Manager</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            {editingUser && (
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="is_active"
                                        checked={form.is_active}
                                        onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                                        className="w-4 h-4"
                                        data-testid="user-active-checkbox"
                                    />
                                    <label htmlFor="is_active" className="text-sm text-slate-600">Active</label>
                                </div>
                            )}
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-user-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingUser ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UsersPage;
