import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Search, UserPlus, X } from 'lucide-react';

interface User {
    id: string;
    name: string;
    email: string;
    role: string;
    is_admin: boolean;
    published_agents: number;
    created_at: string;
}

const ROLES = ['ORG_ADMIN', 'ORG_USER', 'PUBLISHER'];
const ACCESS_TYPES = [
    { value: 'PASSWORD', label: 'Set Temporary Password', description: 'Admin sets an initial password for the user' },
    { value: 'RESET_EMAIL', label: 'Send Password Reset Email', description: 'User receives an email to set their password (Coming Soon)' },
    { value: 'MAGIC_LINK', label: 'Magic Link Login', description: 'User receives a login link each time (Coming Soon)' }
];

export function RolesPage() {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [showRoleModal, setShowRoleModal] = useState(false);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [newRole, setNewRole] = useState('');

    // Invite form state
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteName, setInviteName] = useState('');
    const [inviteRole, setInviteRole] = useState('ORG_USER');
    const [inviteAccessType, setInviteAccessType] = useState('PASSWORD');
    const [invitePassword, setInvitePassword] = useState('');

    useEffect(() => {
        if (currentUser?.id) {
            fetchUsers();
        }
    }, [currentUser?.id]);

    const fetchUsers = async () => {
        try {
            const response = await fetch('/api/v1/admin/users?admin_id=' + currentUser?.id);
            const data = await response.json();
            setUsers(data);
        } catch (error) {
            console.error('Failed to fetch users:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRoleChange = async () => {
        if (!selectedUser || !newRole) return;
        setActionLoading(true);
        try {
            const response = await fetch(
                `/api/v1/admin/users/${selectedUser.id}/role?admin_id=${currentUser?.id}&new_role=${newRole}`,
                { method: 'PUT' }
            );
            if (response.ok) {
                await fetchUsers();
                setShowRoleModal(false);
                setSelectedUser(null);
                setNewRole('');
            }
        } catch (error) {
            console.error('Failed to update role:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const handleInviteUser = async () => {
        if (!inviteEmail) return;
        if (inviteAccessType === 'PASSWORD' && !invitePassword) {
            alert('Please enter a temporary password');
            return;
        }
        setActionLoading(true);
        try {
            const params = new URLSearchParams({
                admin_id: currentUser?.id || '',
                email: inviteEmail,
                role: inviteRole,
                access_type: inviteAccessType
            });
            if (inviteName) params.append('name', inviteName);
            if (inviteAccessType === 'PASSWORD') params.append('password', invitePassword);

            const response = await fetch(`/api/v1/admin/users/invite?${params}`, { method: 'POST' });
            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                await fetchUsers();
                setShowInviteModal(false);
                setInviteEmail('');
                setInviteName('');
                setInviteRole('ORG_USER');
                setInviteAccessType('PASSWORD');
                setInvitePassword('');
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to invite user');
            }
        } catch (error) {
            console.error('Failed to invite user:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const filteredUsers = users.filter(u =>
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
    );

    const getRoleBadge = (role: string) => {
        switch (role?.toUpperCase()) {
            case 'ORG_ADMIN':
                return <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1"><Shield className="w-3 h-3" />Admin</span>;
            case 'PUBLISHER':
                return <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium">Publisher</span>;
            default:
                return <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-medium">User</span>;
        }
    };

    if (loading) {
        return <div className="p-8 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-2 border-green-600 border-t-transparent" /></div>;
    }

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            <div className="flex justify-between items-start mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">User Roles & Permissions</h1>
                    <p className="text-gray-500 mt-1">Manage user access and invite new users</p>
                </div>
                <button
                    onClick={() => setShowInviteModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                >
                    <UserPlus className="w-5 h-5" />
                    Invite User
                </button>
            </div>

            {/* Search */}
            <div className="mb-6">
                <div className="relative max-w-md">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                        type="text"
                        placeholder="Search users..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                </div>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">User</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Role</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Agents</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Joined</th>
                            <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {filteredUsers.map(user => (
                            <tr key={user.id} className="hover:bg-gray-50">
                                <td className="px-6 py-4">
                                    <div className="font-medium text-gray-900">{user.name}</div>
                                    <div className="text-sm text-gray-500">{user.email}</div>
                                </td>
                                <td className="px-6 py-4">{getRoleBadge(user.role)}</td>
                                <td className="px-6 py-4 text-gray-600">{user.published_agents}</td>
                                <td className="px-6 py-4 text-sm text-gray-600">
                                    {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                                </td>
                                <td className="px-6 py-4">
                                    {user.id !== currentUser?.id && (
                                        <button
                                            onClick={() => {
                                                setSelectedUser(user);
                                                setNewRole(user.role);
                                                setShowRoleModal(true);
                                            }}
                                            className="text-sm text-green-600 hover:text-green-700 font-medium"
                                        >
                                            Change Role
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Role Change Modal */}
            {showRoleModal && selectedUser && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowRoleModal(false)}>
                    <div className="bg-white rounded-xl p-6 max-w-md w-full m-4" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-gray-900">Change User Role</h3>
                            <button onClick={() => setShowRoleModal(false)} className="text-gray-400 hover:text-gray-600">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <p className="text-gray-600 mb-4">
                            Update role for <strong>{selectedUser.name}</strong> ({selectedUser.email})
                        </p>
                        <select
                            value={newRole}
                            onChange={(e) => setNewRole(e.target.value)}
                            className="w-full p-3 border border-gray-200 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-green-500"
                        >
                            {ROLES.map(role => (
                                <option key={role} value={role}>{role}</option>
                            ))}
                        </select>
                        <div className="flex gap-3">
                            <button
                                onClick={handleRoleChange}
                                disabled={actionLoading || newRole === selectedUser.role}
                                className="flex-1 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                            >
                                {actionLoading ? 'Updating...' : 'Update Role'}
                            </button>
                            <button
                                onClick={() => setShowRoleModal(false)}
                                className="flex-1 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Invite User Modal */}
            {showInviteModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowInviteModal(false)}>
                    <div className="bg-white rounded-xl p-6 max-w-md w-full m-4" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-gray-900">Invite User</h3>
                            <button onClick={() => setShowInviteModal(false)} className="text-gray-400 hover:text-gray-600">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Email*</label>
                                <input
                                    type="email"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                    placeholder="user@example.com"
                                    className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                <input
                                    type="text"
                                    value={inviteName}
                                    onChange={(e) => setInviteName(e.target.value)}
                                    placeholder="John Doe"
                                    className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                                <select
                                    value={inviteRole}
                                    onChange={(e) => setInviteRole(e.target.value)}
                                    className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                                >
                                    {ROLES.map(role => (
                                        <option key={role} value={role}>{role}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Access Method</label>
                                <div className="space-y-2">
                                    {ACCESS_TYPES.map(type => (
                                        <label
                                            key={type.value}
                                            className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${inviteAccessType === type.value
                                                    ? 'border-green-500 bg-green-50'
                                                    : 'border-gray-200 hover:border-gray-300'
                                                } ${type.value !== 'PASSWORD' ? 'opacity-60' : ''}`}
                                        >
                                            <input
                                                type="radio"
                                                name="accessType"
                                                value={type.value}
                                                checked={inviteAccessType === type.value}
                                                onChange={(e) => setInviteAccessType(e.target.value)}
                                                disabled={type.value !== 'PASSWORD'}
                                                className="mt-1 mr-3"
                                            />
                                            <div>
                                                <div className="font-medium text-gray-900">{type.label}</div>
                                                <div className="text-sm text-gray-500">{type.description}</div>
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {inviteAccessType === 'PASSWORD' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Temporary Password*</label>
                                    <input
                                        type="password"
                                        value={invitePassword}
                                        onChange={(e) => setInvitePassword(e.target.value)}
                                        placeholder="Enter password for user"
                                        className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">User can change this after first login</p>
                                </div>
                            )}
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={handleInviteUser}
                                disabled={actionLoading || !inviteEmail}
                                className="flex-1 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                            >
                                {actionLoading ? 'Inviting...' : 'Send Invite'}
                            </button>
                            <button
                                onClick={() => setShowInviteModal(false)}
                                className="flex-1 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

