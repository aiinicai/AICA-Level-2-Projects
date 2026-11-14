import React, { useState, useEffect, useMemo } from 'react';
import { 
  FileText, Plus, CheckCircle2, Clock, ArrowRight, 
  Search, Filter, TrendingUp, ShieldAlert, Sparkles,
  UserPlus, Building, X, Trash2, AlertTriangle, Award, Check,
  ShieldCheck, MapPin, RefreshCw, Sliders
} from 'lucide-react';
import { Proposal, Client, ProductType, ProposalStatus, PANValidationResult } from '../types';
import { formatINR, formatProductType, formatProposalStatus, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';
import { NumberInput } from './NumberInput';
import { EditRequirementsModal } from './EditRequirementsModal';

interface ProposalPipelineProps {
  proposals: Proposal[];
  clients: Client[];
  selectedProposalId: string | null;
  onSelectProposal: (id: string) => void;
  onCreateProposal: (data: {
    client_id: string;
    entity_id: string;
    product_type: ProductType;
    requested_amount: number;
    tenure_months: number;
    purpose: string;
    target_rate: number;
  }) => Promise<any>;
  onLoadSyntheticDemo: (persona: 'home_loan' | 'lap' | 'tech_sme') => void;
  onRefresh?: () => Promise<void>;
  unitMode: NumberUnitMode;
  onOpenWizard?: (info: {
    id: string;
    code: string;
    clientName?: string;
    productType?: string;
    requestedAmount?: number | string;
  }) => void;
}

export const ProposalPipeline: React.FC<ProposalPipelineProps> = ({
  proposals,
  clients,
  selectedProposalId,
  onSelectProposal,
  onCreateProposal,
  onLoadSyntheticDemo,
  onRefresh,
  unitMode,
  onOpenWizard,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProduct, setFilterProduct] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showOnboardModal, setShowOnboardModal] = useState(false);
  const [editTargetProposal, setEditTargetProposal] = useState<Proposal | null>(null);

  // Form state for Onboard New Customer
  const [onboardForm, setOnboardForm] = useState({
    customer_name: '',
    constitution: 'pvt_ltd',
    primary_contact: '',
    phone: '',
    email: '',
    city: 'Vadodara',
    state: 'Gujarat',
    pan: '',
    promoter_name: '',
    cibil_score: 750,
    product_type: 'cash_credit_od' as ProductType,
    requested_amount: 10000000,
    tenure_months: 60,
    purpose: 'Working capital facilities against receivables and enterprise orders',
  });

  // Form state for new proposal
  const [selectedClientId, setSelectedClientId] = useState('');
  const [selectedEntityId, setSelectedEntityId] = useState('');
  const [productType, setProductType] = useState<ProductType>('cash_credit_od');
  const [requestedAmount, setRequestedAmount] = useState<number>(10000000); // 1 Cr
  const [tenureMonths, setTenureMonths] = useState<number>(60);
  const [purpose, setPurpose] = useState('');
  const [targetRate, setTargetRate] = useState<number>(9.25);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Master Cities & States LOV with Auto-Prompt & Auto-Fill
  const [citiesList, setCitiesList] = useState<Array<{ city: string; state: string }>>([]);
  const [statesList, setStatesList] = useState<string[]>([]);
  const [panValidation, setPanValidation] = useState<PANValidationResult | null>(null);
  const [isVerifyingPan, setIsVerifyingPan] = useState(false);

  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const [cts, sts] = await Promise.all([
          ApiClient.request<Array<{ city: string; state: string }>>('/master/cities?limit=200'),
          ApiClient.request<string[]>('/master/states'),
        ]);
        setCitiesList(cts);
        setStatesList(sts);
      } catch (err) {
        console.warn('Failed to load master cities/states:', err);
      }
    };
    fetchLocations();
  }, []);

  const handleCityChange = (cityName: string) => {
    // Check if city matches any pre-seeded city in LOV to auto-fill state
    const matched = citiesList.find(
      (c) => c.city.trim().toLowerCase() === cityName.trim().toLowerCase()
    );
    if (matched) {
      setOnboardForm((prev) => ({
        ...prev,
        city: cityName,
        state: matched.state, // Auto-prompt & auto-fill state!
      }));
    } else {
      // LOV is NOT restrictive - user can type any city
      setOnboardForm((prev) => ({ ...prev, city: cityName }));
    }
  };

  const handleValidatePan = async (panStr: string, name?: string, constType?: string) => {
    const cleanPan = panStr.trim().toUpperCase();
    if (!cleanPan || cleanPan.length < 10) {
      setPanValidation(null);
      return;
    }
    setIsVerifyingPan(true);
    try {
      const res = await ApiClient.request<PANValidationResult>('/master/pan/validate', {
        method: 'POST',
        body: JSON.stringify({
          pan: cleanPan,
          entity_name: name || onboardForm.customer_name,
          constitution: constType || onboardForm.constitution,
        }),
      });
      setPanValidation(res);
    } catch (err) {
      console.warn('PAN validation error:', err);
    } finally {
      setIsVerifyingPan(false);
    }
  };

  // Calculate Pipeline Metrics
  const totalPipelineAmount = proposals.reduce((sum, p) => sum + Number(p.requested_amount || 0), 0);
  const pendingReviewCount = proposals.filter(p => p.status === 'reviewer_approval').length;
  const underExtractionCount = proposals.filter(p => p.status === 'extraction_verification' || p.status === 'document_collection').length;
  const closedWonCount = proposals.filter(p => p.status === 'closed_won' || p.status === 'sanctioned').length;
  const closedLostCount = proposals.filter(p => p.status === 'closed_lost' || p.status === 'rejected').length;

  const filteredProposals = proposals.filter((p) => {
    const matchesSearch = p.proposal_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.product_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesProduct = filterProduct === 'all' || p.product_type === filterProduct;
    let matchesStatus = true;
    if (filterStatus === 'active') {
      matchesStatus = p.status !== 'closed_won' && p.status !== 'closed_lost' && p.status !== 'sanctioned' && p.status !== 'rejected';
    } else if (filterStatus === 'closed_won') {
      matchesStatus = p.status === 'closed_won' || p.status === 'sanctioned';
    } else if (filterStatus === 'closed_lost') {
      matchesStatus = p.status === 'closed_lost' || p.status === 'rejected';
    }
    return matchesSearch && matchesProduct && matchesStatus;
  });

  const handleDirectDelete = async (id: string, code: string) => {
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete proposal ${code}?\n\nThis will remove all associated documents, extracted metrics, and underwriting evaluations.`
    );
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      await ApiClient.request(`/proposals/${id}`, {
        method: 'DELETE',
      });
      alert(`Proposal ${code} deleted successfully.`);
      if (onRefresh) {
        await onRefresh();
      }
    } catch (err: any) {
      alert(err.message || 'Error deleting proposal');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleQuickStatusChange = async (proposalId: string, newStatus: ProposalStatus) => {
    try {
      await ApiClient.request(`/proposals/${proposalId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      if (onRefresh) {
        await onRefresh();
      }
    } catch (err: any) {
      alert(err.message || 'Error updating proposal status');
    }
  };

  const activeClients = useMemo(() => clients.filter(c => !c.is_deleted), [clients]);

  const handleOpenModal = () => {
    if (activeClients.length > 0) {
      setSelectedClientId(activeClients[0].id);
      if (activeClients[0].entities && activeClients[0].entities.length > 0) {
        setSelectedEntityId(activeClients[0].entities[0].id);
      } else {
        setSelectedEntityId('');
      }
    } else {
      setSelectedClientId('');
      setSelectedEntityId('');
    }
    setShowCreateModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClientId || !selectedEntityId) {
      alert('Please select or create a client and entity first.');
      return;
    }
    setIsSubmitting(true);
    try {
      await onCreateProposal({
        client_id: selectedClientId,
        entity_id: selectedEntityId,
        product_type: productType,
        requested_amount: requestedAmount,
        tenure_months: tenureMonths,
        purpose,
        target_rate: targetRate,
      });
      setShowCreateModal(false);
    } catch (err: any) {
      alert(err.message || 'Error creating proposal');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOnboardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onboardForm.customer_name || !onboardForm.phone || !onboardForm.email) {
      alert('Please fill in required fields: Customer Name, Phone, and Email');
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await ApiClient.request<any>('/clients/onboard', {
        method: 'POST',
        body: JSON.stringify({
          ...onboardForm,
          create_proposal: true,
        }),
      });
      setShowOnboardModal(false);
      if (onRefresh) {
        await onRefresh();
      }
      if (res.proposal_id) {
        onSelectProposal(res.proposal_id);
        if (onOpenWizard) {
          onOpenWizard({
            id: res.proposal_id,
            code: res.proposal_code,
            clientName: onboardForm.customer_name,
            productType: onboardForm.product_type,
            requestedAmount: onboardForm.requested_amount,
          });
        }
      }
    } catch (err: any) {
      alert(err.message || 'Onboarding error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-2.5 bg-brand-50 text-brand-700 rounded-lg">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase">Total Proposals</p>
            <p className="text-lg font-bold text-slate-900">{proposals.length}</p>
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-2.5 bg-emerald-50 text-emerald-700 rounded-lg">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase">Syndication Pipeline</p>
            <p className="text-lg font-bold text-slate-900">{formatINR(totalPipelineAmount, unitMode)}</p>
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-2.5 bg-amber-50 text-amber-700 rounded-lg">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase">Reviewer Queue</p>
            <p className="text-lg font-bold text-slate-900">{pendingReviewCount} Cases</p>
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-2.5 bg-emerald-100 text-emerald-800 rounded-lg">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-emerald-700 uppercase">Closed - Won</p>
            <p className="text-lg font-bold text-emerald-900">{closedWonCount} Cases</p>
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
          <div className="p-2.5 bg-rose-50 text-rose-700 rounded-lg">
            <X className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold text-rose-700 uppercase">Closed - Not Won</p>
            <p className="text-lg font-bold text-rose-900">{closedLostCount} Cases</p>
          </div>
        </div>
      </div>

      {/* Demo Persona Action Bar */}
      <div className="bg-gradient-to-r from-[#1b2632] via-[#243343] to-[#1b2632] text-white rounded-xl p-4 shadow-md flex flex-wrap items-center justify-between gap-3 border border-[#2a3c4f]">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[#ebb9ab]" />
          <div>
            <span className="font-semibold text-sm">Synthetic Reference Dossiers (Instant 1-Click Load):</span>
            <p className="text-xs text-slate-300">Load test personas configured with complete Indian banking documentation & financial figures.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onLoadSyntheticDemo('tech_sme')}
            className="px-3 py-1.5 text-xs font-medium bg-[#1b2632] hover:bg-[#a45139] rounded-lg border border-[#a45139]/50 transition-colors text-slate-100"
          >
            SME Working Capital (₹1 Cr CC/OD)
          </button>
          <button
            onClick={() => onLoadSyntheticDemo('lap')}
            className="px-3 py-1.5 text-xs font-medium bg-[#1b2632] hover:bg-[#a45139] rounded-lg border border-[#a45139]/50 transition-colors text-slate-100"
          >
            Self-Employed LAP (₹75 Lakhs)
          </button>
          <button
            onClick={() => onLoadSyntheticDemo('home_loan')}
            className="px-3 py-1.5 text-xs font-medium bg-[#1b2632] hover:bg-[#a45139] rounded-lg border border-[#a45139]/50 transition-colors text-slate-100"
          >
            Salaried Home Loan (₹50 Lakhs)
          </button>
        </div>
      </div>

      {/* Pipeline Filter & Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search proposal code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <select
            value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="all">All Products</option>
            <option value="cash_credit_od">Cash Credit / Overdraft</option>
            <option value="home_loan">Home Loan</option>
            <option value="lap">Loan Against Property</option>
            <option value="business_loan_secured">Business Loan</option>
            <option value="project_finance_term_loan">Project Finance</option>
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="all">All Stages ({proposals.length})</option>
            <option value="active">Active Pipeline ({proposals.length - closedWonCount - closedLostCount})</option>
            <option value="closed_won">🏆 Closed - Won ({closedWonCount})</option>
            <option value="closed_lost">✕ Closed - Not Won ({closedLostCount})</option>
          </select>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => setShowOnboardModal(true)}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2 bg-emerald-700 text-white rounded-lg text-xs font-semibold hover:bg-emerald-800 shadow-sm transition-all"
            title="Onboard a brand new borrower / customer & initialize proposal"
          >
            <UserPlus className="w-4 h-4" />
            <span>+ Onboard New Customer</span>
          </button>

          <button
            onClick={handleOpenModal}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2 bg-[#a45139] hover:bg-[#863e2a] text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            title="Create facility proposal for existing client"
          >
            <Plus className="w-4 h-4" />
            <span>New Facility Proposal</span>
          </button>
        </div>
      </div>

      {/* Proposals Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
            <tr>
              <th className="py-3 px-4">Proposal Code</th>
              <th className="py-3 px-4">Borrower Entity</th>
              <th className="py-3 px-4">Loan Product</th>
              <th className="py-3 px-4 text-right">Requested Amount</th>
              <th className="py-3 px-4">Tenure</th>
              <th className="py-3 px-4">Stage Status</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredProposals.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400 italic">
                  No proposals found matching the filter criteria.
                </td>
              </tr>
            ) : (
              filteredProposals.map((prop) => {
                const statusMeta = formatProposalStatus(prop.status);
                const isSelected = prop.id === selectedProposalId;
                return (
                  <tr
                    key={prop.id}
                    className={`hover:bg-slate-50/80 transition-colors ${
                      isSelected ? 'bg-brand-50/60 font-medium' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-brand-900">{prop.proposal_code}</td>
                    <td className="py-3 px-4 text-slate-900">
                      {clients.find(c => c.id === prop.client_id)?.primary_contact_name || 'Borrower'}
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200 text-[11px]">
                        {formatProductType(prop.product_type)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-900">
                      {formatINR(prop.requested_amount, unitMode)}
                    </td>
                    <td className="py-3 px-4 text-slate-600">{prop.tenure_months} M</td>
                    <td className="py-3 px-4">
                      <div className="flex flex-col gap-1 items-start">
                        <span className={`inline-block px-2.5 py-1 rounded-full border text-[11px] font-medium ${statusMeta.color}`}>
                          {statusMeta.label}
                        </span>
                        <div className="flex items-center gap-1.5 opacity-80 hover:opacity-100 transition-opacity">
                          {prop.status !== 'closed_won' && (
                            <button
                              onClick={() => handleQuickStatusChange(prop.id, 'closed_won')}
                              title="Mark proposal as Won (Sanctioned)"
                              className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 font-medium"
                            >
                              ✓ Won
                            </button>
                          )}
                          {prop.status !== 'closed_lost' && (
                            <button
                              onClick={() => handleQuickStatusChange(prop.id, 'closed_lost')}
                              title="Mark proposal as Not Won"
                              className="px-1.5 py-0.5 rounded text-[10px] bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 font-medium"
                            >
                              ✕ Not Won
                            </button>
                          )}
                          {(prop.status === 'closed_won' || prop.status === 'closed_lost') && (
                            <button
                              onClick={() => handleQuickStatusChange(prop.id, 'reviewer_approval')}
                              title="Re-open to Reviewer Approval"
                              className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 font-medium"
                            >
                              Reopen
                            </button>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setEditTargetProposal(prop)}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-[#a45139] hover:bg-[#faece7] border border-slate-200 hover:border-[#f5d7cf] transition-colors"
                          title={`Edit loan requirements for ${prop.proposal_code}`}
                        >
                          <Sliders className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onSelectProposal(prop.id)}
                          className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            isSelected
                              ? 'bg-[#a45139] text-white shadow-sm'
                              : 'bg-[#1b2632] hover:bg-[#243343] text-white shadow-2xs'
                          }`}
                        >
                          <span>Workspace</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDirectDelete(prop.id, prop.proposal_code)}
                          disabled={isDeleting}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors cursor-pointer"
                          title={`Permanently delete proposal ${prop.proposal_code}`}
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

      {/* New Proposal Modal Dialog */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create New Loan Proposal</h3>
            <p className="text-xs text-slate-500 mb-4">
              Initiates the syndication workflow, pre-populates the 7-column primary checklist, and sets up preliminary eligibility tracking.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block font-semibold text-slate-700">Target Client Profile</label>
                  {activeClients.length > 0 && (
                    <span className="text-[11px] text-slate-500 font-normal">
                      {activeClients.length} active customer{activeClients.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                {activeClients.length === 0 ? (
                  <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-2.5">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-semibold text-amber-900">No Active Customer Profiles Available</p>
                        <p className="text-amber-700 leading-relaxed text-[11px] mt-0.5">
                          Deleted customers are excluded. To create a facility proposal, please onboard a customer profile first.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowCreateModal(false);
                        setShowOnboardModal(true);
                      }}
                      className="w-full py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-semibold text-xs shadow-xs flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>+ Onboard New Customer</span>
                    </button>
                  </div>
                ) : (
                  <select
                    value={selectedClientId}
                    onChange={(e) => {
                      setSelectedClientId(e.target.value);
                      const c = activeClients.find(cl => cl.id === e.target.value);
                      if (c && c.entities && c.entities.length > 0) {
                        setSelectedEntityId(c.entities[0].id);
                      }
                    }}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
                    required
                  >
                    {activeClients.map(c => {
                      const entityName = c.entities && c.entities.length > 0 ? c.entities[0].legal_name : c.primary_contact_name;
                      return (
                        <option key={c.id} value={c.id}>
                          {entityName} ({c.constitution}) • {c.client_code}
                        </option>
                      );
                    })}
                  </select>
                )}
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Facility / Loan Product</label>
                <select
                  value={productType}
                  onChange={(e) => setProductType(e.target.value as ProductType)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                  required
                >
                  <option value="cash_credit_od">Cash Credit / Overdraft (CC/OD)</option>
                  <option value="working_capital">Working Capital Term Facility</option>
                  <option value="home_loan">Home Loan (Purchase / Construction)</option>
                  <option value="lap">Loan Against Property (LAP)</option>
                  <option value="business_loan_secured">Secured Business Loan</option>
                  <option value="business_loan_unsecured">Unsecured Business Loan</option>
                  <option value="project_finance_term_loan">Project Finance & Term Loan</option>
                  <option value="balance_transfer_topup">Balance Transfer & Top-up</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Requested Loan (INR ₹)</label>
                  <NumberInput
                    value={requestedAmount}
                    onChange={setRequestedAmount}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                    required
                    min={100000}
                    step={50000}
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Tenure (Months)</label>
                  <NumberInput
                    value={tenureMonths}
                    onChange={setTenureMonths}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                    required
                    min={1}
                    max={360}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Rate of Interest (% p.a.)</label>
                  <NumberInput
                    value={targetRate}
                    onChange={setTargetRate}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                    step={0.05}
                    min={5}
                    max={30}
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Facility Purpose</label>
                  <input
                    type="text"
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    placeholder="e.g. Working capital against debtors"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || activeClients.length === 0}
                  className={`px-5 py-2 text-white rounded-lg font-semibold shadow-sm transition-all ${
                    activeClients.length === 0
                      ? 'bg-slate-300 cursor-not-allowed text-slate-500'
                      : 'bg-[#a45139] hover:bg-[#863e2a]'
                  }`}
                  title={activeClients.length === 0 ? 'Please onboard a customer first' : 'Initialize Proposal'}
                >
                  {isSubmitting ? 'Creating...' : 'Initialize Proposal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Onboard New Customer Modal Dialog */}
      {showOnboardModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-emerald-50 text-emerald-800 rounded-lg">
                  <UserPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Onboard New Customer &amp; Loan Proposal</h3>
                  <p className="text-xs text-slate-500">Provisions Client, Entity, Promoter KYC, and initializes the 7-column primary checklist.</p>
                </div>
              </div>
              <button
                onClick={() => setShowOnboardModal(false)}
                className="p-1 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleOnboardSubmit} className="space-y-4 text-xs pt-4">
              {/* Section 1: Business Identity */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-3">
                <p className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-brand-700" />
                  <span>Borrower / Entity Profile</span>
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Company / Customer Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Apex BioPharma Private Limited"
                      value={onboardForm.customer_name}
                      onChange={(e) => setOnboardForm({ ...onboardForm, customer_name: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Constitution *</label>
                    <select
                      value={onboardForm.constitution}
                      onChange={(e) => setOnboardForm({ ...onboardForm, constitution: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    >
                      <option value="pvt_ltd">Private Limited Company</option>
                      <option value="public_ltd">Public Limited Company</option>
                      <option value="llp">Limited Liability Partnership (LLP)</option>
                      <option value="partnership">Partnership Firm</option>
                      <option value="proprietorship">Sole Proprietorship</option>
                      <option value="salaried">Salaried Individual</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block font-semibold text-slate-700">Entity PAN</label>
                      <button
                        type="button"
                        onClick={() => handleValidatePan(onboardForm.pan, onboardForm.customer_name, onboardForm.constitution)}
                        disabled={isVerifyingPan || onboardForm.pan.length < 10}
                        className="text-[10px] text-[#a45139] hover:underline font-bold cursor-pointer disabled:opacity-40"
                      >
                        {isVerifyingPan ? 'Verifying...' : 'Validate PAN'}
                      </button>
                    </div>
                    <input
                      type="text"
                      maxLength={10}
                      placeholder="e.g. AAACX0000M"
                      value={onboardForm.pan}
                      onChange={(e) => {
                        const val = e.target.value.toUpperCase();
                        setOnboardForm({ ...onboardForm, pan: val });
                        if (val.length === 10) {
                          handleValidatePan(val, onboardForm.customer_name, onboardForm.constitution);
                        } else {
                          setPanValidation(null);
                        }
                      }}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800 uppercase font-mono tracking-wider"
                    />

                    {/* Real-time PAN Validation Indicator */}
                    {panValidation && (
                      <div className={`mt-1.5 p-2 rounded-lg text-[11px] leading-tight flex items-start gap-1.5 border ${
                        panValidation.is_valid && panValidation.constitution_match
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : panValidation.is_valid && !panValidation.constitution_match
                          ? 'bg-amber-50 text-amber-800 border-amber-200'
                          : 'bg-rose-50 text-rose-800 border-rose-200'
                      }`}>
                        {panValidation.is_valid && panValidation.constitution_match ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <div className="font-bold">
                            {panValidation.pan_type} ({panValidation.entity_type_code}): {panValidation.status}
                          </div>
                          <div className="text-[10px] opacity-90 mt-0.5">{panValidation.message}</div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      City &amp; State <span className="text-[10px] text-slate-400 font-normal">(Auto-fill from LOV or type new)</span>
                    </label>
                    <div className="grid grid-cols-2 gap-1.5">
                      <div>
                        <input
                          type="text"
                          list="india-cities-lov"
                          placeholder="Type City..."
                          value={onboardForm.city}
                          onChange={(e) => handleCityChange(e.target.value)}
                          className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                        />
                        <datalist id="india-cities-lov">
                          {citiesList.map((c, i) => (
                            <option key={i} value={c.city}>
                              {c.city} ({c.state})
                            </option>
                          ))}
                        </datalist>
                      </div>

                      <div>
                        <input
                          type="text"
                          list="india-states-lov"
                          placeholder="Type State..."
                          value={onboardForm.state}
                          onChange={(e) => setOnboardForm({ ...onboardForm, state: e.target.value })}
                          className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                        />
                        <datalist id="india-states-lov">
                          {statesList.map((s, i) => (
                            <option key={i} value={s} />
                          ))}
                        </datalist>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 2: Contact Person & Promoter */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-3">
                <p className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">
                  Contact &amp; Key Promoter KYC
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Primary Contact *</label>
                    <input
                      type="text"
                      placeholder="e.g. Rajesh Shah"
                      value={onboardForm.primary_contact}
                      onChange={(e) => setOnboardForm({ ...onboardForm, primary_contact: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Phone Number *</label>
                    <input
                      type="tel"
                      required
                      placeholder="+91 98765 43210"
                      value={onboardForm.phone}
                      onChange={(e) => setOnboardForm({ ...onboardForm, phone: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Email Address *</label>
                    <input
                      type="email"
                      required
                      placeholder="borrower@example.com"
                      value={onboardForm.email}
                      onChange={(e) => setOnboardForm({ ...onboardForm, email: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Director / Promoter Name</label>
                    <input
                      type="text"
                      placeholder="Promoter / Managing Director"
                      value={onboardForm.promoter_name}
                      onChange={(e) => setOnboardForm({ ...onboardForm, promoter_name: e.target.value })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Promoter CIBIL Score</label>
                    <NumberInput
                      min={300}
                      max={900}
                      placeholder="750"
                      value={onboardForm.cibil_score}
                      onChange={(val) => setOnboardForm({ ...onboardForm, cibil_score: val })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                </div>
              </div>

              {/* Section 3: Initial Loan Facility Request */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-3">
                <p className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">
                  Initial Facility Request
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Facility Product</label>
                    <select
                      value={onboardForm.product_type}
                      onChange={(e) => setOnboardForm({ ...onboardForm, product_type: e.target.value as ProductType })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    >
                      <option value="cash_credit_od">Cash Credit / Overdraft</option>
                      <option value="working_capital">Working Capital Term Loan</option>
                      <option value="business_loan_secured">Secured Business Loan</option>
                      <option value="business_loan_unsecured">Unsecured Business Loan</option>
                      <option value="lap">Loan Against Property</option>
                      <option value="home_loan">Home Loan</option>
                      <option value="project_finance_term_loan">Project Finance</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Requested Amount (₹ INR)</label>
                    <NumberInput
                      min={100000}
                      step={50000}
                      value={onboardForm.requested_amount}
                      onChange={(val) => setOnboardForm({ ...onboardForm, requested_amount: val })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Tenure (Months)</label>
                    <NumberInput
                      min={6}
                      max={360}
                      value={onboardForm.tenure_months}
                      onChange={(val) => setOnboardForm({ ...onboardForm, tenure_months: val })}
                      className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Purpose / End-Use</label>
                  <input
                    type="text"
                    value={onboardForm.purpose}
                    onChange={(e) => setOnboardForm({ ...onboardForm, purpose: e.target.value })}
                    className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800"
                  />
                </div>
              </div>

              {/* Submit / Cancel */}
              <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowOnboardModal(false)}
                  className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-semibold shadow-sm transition-all"
                >
                  {isSubmitting ? 'Onboarding...' : '✓ Complete Onboarding & Open Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Loan Requirements Modal Dialog */}
      {editTargetProposal && (
        <EditRequirementsModal
          proposal={editTargetProposal}
          borrowerName={
            clients.find(c => c.id === editTargetProposal.client_id)?.primary_contact_name ||
            'Borrower'
          }
          unitMode={unitMode}
          onClose={() => setEditTargetProposal(null)}
          onSuccess={async () => {
            setEditTargetProposal(null);
            if (onRefresh) await onRefresh();
          }}
        />
      )}
    </div>
  );
};
