import React, { useState, useMemo } from 'react';
import {
  Users,
  Search,
  Plus,
  Eye,
  Edit,
  Trash2,
  FileSpreadsheet,
  FilePlus,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Building2,
  Phone,
  Mail,
  MapPin,
  TrendingUp,
  Tag
} from 'lucide-react';
import { Client, Voucher } from '../../types';
import { StorageService } from '../../services/storage';

interface ClientListProps {
  clients: Client[];
  vouchers: Voucher[];
  onOpenClientDetail: (client: Client) => void;
  onOpenClientForm: (client?: Client) => void;
  onDeleteClient: (clientId: string) => void;
  onCreateVoucherForClient: (client: Client) => void;
  onOpenBulkImport: () => void;
}

export const ClientList: React.FC<ClientListProps> = ({
  clients,
  vouchers,
  onOpenClientDetail,
  onOpenClientForm,
  onDeleteClient,
  onCreateVoucherForClient,
  onOpenBulkImport,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState<string>('ALL');
  const [filterOverdueOnly, setFilterOverdueOnly] = useState<boolean>(false);

  const storage = StorageService.getInstance();
  const crmAnalytics = useMemo(() => {
    return storage.getCRMAnalytics();
  }, [clients, vouchers]);

  // Aggregate all unique tags across clients
  const allTags = useMemo(() => {
    const set = new Set<string>();
    clients.forEach((c) => c.tags?.forEach((t) => set.add(t)));
    return Array.from(set);
  }, [clients]);

  // Filtered clients
  const filteredClients = useMemo(() => {
    return clients.filter((c) => {
      const matchSearch =
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.contactPerson.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.tin.includes(searchTerm) ||
        c.mobile.includes(searchTerm);

      const matchTag = selectedTag === 'ALL' || c.tags?.includes(selectedTag);

      const analytics = crmAnalytics.find((a) => a.client.id === c.id);
      const matchOverdue = !filterOverdueOnly || analytics?.isOverdueForOrder;

      return matchSearch && matchTag && matchOverdue;
    });
  }, [clients, searchTerm, selectedTag, filterOverdueOnly, crmAnalytics]);

  const overdueCount = useMemo(() => {
    return crmAnalytics.filter((a) => a.isOverdueForOrder).length;
  }, [crmAnalytics]);

  return (
    <div id="clientele-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Clients */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-xs text-slate-500 font-medium">Total Registered Clients</p>
          <p className="text-lg font-bold text-slate-900 mt-1 font-mono">{clients.length}</p>
          <p className="text-[11px] text-emerald-600 font-medium mt-0.5">Verified TRA TIN Master</p>
        </div>

        {/* Overdue for Repeat Order */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-xs text-slate-500 font-medium">Overdue for Repeat Order</p>
          <p className="text-lg font-bold text-amber-600 mt-1 font-mono">{overdueCount} Accounts</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Exceeds average order cycle</p>
        </div>

        {/* Active Accounts */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-xs text-slate-500 font-medium">Total Sales Transactions</p>
          <p className="text-lg font-bold text-slate-900 mt-1 font-mono">
            {vouchers.filter((v) => v.type === 'SALES').length} Invoices
          </p>
          <p className="text-[11px] text-blue-600 font-medium mt-0.5">Commercial volume</p>
        </div>

        {/* VAT Registered Ratio */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-xs text-slate-500 font-medium">VAT Registered Ratio</p>
          <p className="text-lg font-bold text-slate-900 mt-1 font-mono">
            {clients.filter((c) => c.isVatRegistered).length} / {clients.length}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">TRA Registered Entities</p>
        </div>
      </div>

      {/* Control Bar: Search & Action Buttons */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by client name, contact person, TIN (102-491-884)..."
            className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-slate-800"
          />
        </div>

        {/* Tag Filters & Overdue Toggle */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Tag selector */}
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white"
          >
            <option value="ALL">All Industry Tags</option>
            {allTags.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          {/* Overdue filter toggle button */}
          <button
            onClick={() => setFilterOverdueOnly(!filterOverdueOnly)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              filterOverdueOnly
                ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Overdue Repeat Orders ({overdueCount})</span>
          </button>

          {/* Bulk Import */}
          <button
            onClick={onOpenBulkImport}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Bulk Import</span>
          </button>

          {/* Add Client Button */}
          <button
            onClick={() => onOpenClientForm()}
            className="flex items-center space-x-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Client</span>
          </button>
        </div>
      </div>

      {/* Clients Directory Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Client Entity</th>
                <th className="py-3 px-4">TRA TIN / VRN</th>
                <th className="py-3 px-4">Contact Info</th>
                <th className="py-3 px-4">Tags & Sector</th>
                <th className="py-3 px-4 text-center">Repeat Order Status</th>
                <th className="py-3 px-4 text-right">Total Invoiced</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredClients.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No client records match your search criteria.
                  </td>
                </tr>
              ) : (
                filteredClients.map((client) => {
                  const analytics = crmAnalytics.find((a) => a.client.id === client.id);
                  const isOverdue = analytics?.isOverdueForOrder;
                  const totalSpent = analytics?.totalSpent || 0;
                  const orderCount = analytics?.orderCount || 0;

                  return (
                    <tr key={client.id} className="hover:bg-slate-50/80 transition">
                      {/* Client Entity */}
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900 text-xs">{client.name}</div>
                        <div className="text-[11px] text-slate-500 flex items-center space-x-1 mt-0.5">
                          <MapPin className="w-3 h-3 text-slate-400" />
                          <span className="truncate max-w-xs">{client.address}</span>
                        </div>
                      </td>

                      {/* TRA TIN */}
                      <td className="py-3 px-4">
                        <div className="font-mono font-semibold text-slate-800">{client.tin}</div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {client.isVatRegistered ? 'VAT Registered' : 'Non-VAT'}
                        </div>
                      </td>

                      {/* Contact Info */}
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-800">{client.contactPerson}</div>
                        <div className="text-[10px] text-slate-500 font-mono flex items-center space-x-1">
                          <Phone className="w-3 h-3 text-slate-400" />
                          <span>{client.mobile}</span>
                        </div>
                      </td>

                      {/* Tags */}
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {client.tags?.map((t, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-medium"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Repeat Order Trend Status */}
                      <td className="py-3 px-4 text-center">
                        {isOverdue ? (
                          <div className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-300 animate-pulse">
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            <span>Overdue for Order</span>
                          </div>
                        ) : orderCount > 0 ? (
                          <div className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Active (Avg {analytics?.averageDaysBetweenOrders}d cycle)</span>
                          </div>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-medium">New Client (0 Orders)</span>
                        )}
                      </td>

                      {/* Total Invoiced */}
                      <td className="py-3 px-4 text-right">
                        <div className="font-mono font-bold text-slate-900">
                          TZS {totalSpent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {orderCount} {orderCount === 1 ? 'voucher' : 'vouchers'}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          {/* Create Voucher */}
                          <button
                            title="Create Invoice / PO for this client"
                            onClick={() => onCreateVoucherForClient(client)}
                            className="p-1 text-slate-500 hover:text-blue-600 rounded hover:bg-slate-100 transition"
                          >
                            <FilePlus className="w-4 h-4" />
                          </button>

                          {/* View Details & Timeline */}
                          <button
                            title="View Relationship Timeline & KYC"
                            onClick={() => onOpenClientDetail(client)}
                            className="p-1 text-slate-500 hover:text-emerald-600 rounded hover:bg-slate-100 transition"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* Edit */}
                          <button
                            title="Edit Client Master"
                            onClick={() => onOpenClientForm(client)}
                            className="p-1 text-slate-500 hover:text-indigo-600 rounded hover:bg-slate-100 transition"
                          >
                            <Edit className="w-4 h-4" />
                          </button>

                          {/* Delete */}
                          <button
                            title="Delete Client"
                            onClick={() => {
                              if (window.confirm(`Delete client ${client.name}?`)) {
                                onDeleteClient(client.id);
                              }
                            }}
                            className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-slate-100 transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
