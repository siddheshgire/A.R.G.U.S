import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, 
  ShieldCheck, 
  RefreshCw, 
  UserPlus, 
  CheckCircle2, 
  XCircle,
  Key
} from 'lucide-react';
import { getUsers } from '../api/admin';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getUsers({ limit: 50 });
      setUsers(res.items || []);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError(err.message || 'Failed to retrieve user registry.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Users className="w-6 h-6 text-primary-400" />
            User Access & Role Management
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            System accounts, assigned security roles, and authentication status.
          </p>
        </div>

        <button
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          Refresh Users
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchUsers} className="underline">Retry</button>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">User ID</th>
                <th className="py-3 px-4">Username</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Account Status</th>
                <th className="py-3 px-4">Provisioned Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-400" />
                    Querying user access roster...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-slate-500 font-sans text-xs">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400">#{u.id}</td>
                    <td className="py-3 px-4 font-sans font-bold text-white flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-[10px] text-primary-400 border border-slate-700">
                        {u.username.substring(0, 2).toUpperCase()}
                      </div>
                      {u.username}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' :
                        u.role === 'ANALYST' ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' :
                        u.role === 'AUDITOR' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                        'bg-slate-800 text-slate-300 border border-slate-700'
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans">
                      {u.is_active !== false ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 text-xs font-medium">
                          <XCircle className="w-3.5 h-3.5" /> Inactive
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-sans text-[11px] whitespace-nowrap">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
