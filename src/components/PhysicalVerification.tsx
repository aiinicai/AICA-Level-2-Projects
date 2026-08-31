import React, { useState } from 'react';
import { 
  QrCode, 
  Scan, 
  MapPin, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert
} from 'lucide-react';
import { Asset, PlantLocation, VerificationScanRecord, VerificationStatus, RiskFinding } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface PhysicalVerificationProps {
  assets: Asset[];
  setAssets: React.Dispatch<React.SetStateAction<Asset[]>>;
  scanLogs: VerificationScanRecord[];
  setScanLogs: React.Dispatch<React.SetStateAction<VerificationScanRecord[]>>;
  risks: RiskFinding[];
  setRisks: React.Dispatch<React.SetStateAction<RiskFinding[]>>;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onNavigateToAsset: (assetId: string) => void;
}

export const PhysicalVerification: React.FC<PhysicalVerificationProps> = ({
  assets,
  setAssets,
  scanLogs,
  setScanLogs,
  risks,
  setRisks,
  currencyMode,
  onNavigateToAsset
}) => {
  // Scanner state
  const [selectedScanPlant, setSelectedScanPlant] = useState<PlantLocation>('Pune Plant - Chakan');
  const [selectedSubLocation, setSelectedSubLocation] = useState('Bay 4 - High Precision Machining Cell');
  const [inspectorName, setInspectorName] = useState('Anuj Patil (Internal Audit Lead)');
  const [tagInput, setTagInput] = useState('QR-AST-PUN-CNC-0042');
  const [isScanning, setIsScanning] = useState(false);
  const [latestScanResult, setLatestScanResult] = useState<VerificationScanRecord | null>(scanLogs[0] || null);
  const [matchedAsset, setMatchedAsset] = useState<Asset | null>(
    assets.find((a) => a.qrCode === 'QR-AST-PUN-CNC-0042') || null
  );

  // Filter logs
  const [logFilter, setLogFilter] = useState<'All' | 'Discrepancies' | 'Verified'>('All');

  const plants: PlantLocation[] = [
    'Pune Plant - Chakan',
    'Chennai Automotive Hub',
    'Manesar Tooling Hub',
    'Sanand EV Plant',
    'Bengaluru HQ & Tech Center'
  ];

  // Preset quick tags to simulate real field scenarios
  const quickTestTags = [
    { tag: 'QR-AST-PUN-CNC-0042', label: 'CNC Machine (Pune - Match)' },
    { tag: 'QR-AST-CHN-SMT-0031', label: 'SMT Feeder (Chennai asset scanned in Sanand - Wrong Loc)' },
    { tag: 'QR-AST-BLR-LAB-0019', label: 'Spectrum Analyzer (Bengaluru - Ghost/Missing)' },
    { tag: 'QR-AST-MAN-TLS-0088', label: 'Die Casting Mould (Manesar - Duplicate Tag)' },
    { tag: 'QR-AST-PUN-HYD-0007', label: 'Hydraulic Press (Scrapped Asset)' }
  ];

  const handleSimulateScan = (tagToScan: string = tagInput) => {
    setIsScanning(true);

    setTimeout(() => {
      setIsScanning(false);
      const foundAsset = assets.find((a) => a.qrCode === tagToScan || a.id === tagToScan);

      let detectedStatus: VerificationStatus = 'Verified';
      let discrepancy = false;
      let notes = 'Physical inspection matched asset master.';

      if (!foundAsset) {
        detectedStatus = 'Requires Inspection';
        discrepancy = true;
        notes = 'Unregistered Tag: Tag ID not found in current Fixed Asset Subledger.';
      } else if (foundAsset.status === 'Disposed' || foundAsset.id === 'AST-PUN-HYD-0007') {
        detectedStatus = 'Missing';
        discrepancy = true;
        notes = 'Asset recorded as scrapped/disposed, yet physical tag scanned on shop floor or subledger unretired.';
      } else if (foundAsset.plant !== selectedScanPlant) {
        detectedStatus = 'Wrong Location';
        discrepancy = true;
        notes = `Location Mismatch: Asset registered at [${foundAsset.plant}], but scanned physically at [${selectedScanPlant}]. No STN / e-Way Bill found.`;
      } else if (foundAsset.id === 'AST-BLR-LAB-0019') {
        detectedStatus = 'Suspected Ghost';
        discrepancy = true;
        notes = 'Suspected Ghost Asset: Equipment missing from assigned R&D lab bench.';
      }

      const newRecord: VerificationScanRecord = {
        id: `SCN-${Date.now().toString().slice(-6)}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
        tagScanned: tagToScan,
        assetId: foundAsset?.id || 'UNKNOWN',
        assetName: foundAsset?.name || 'Unidentified Asset',
        scannedPlant: selectedScanPlant,
        scannedSubLocation: selectedSubLocation,
        registeredPlant: foundAsset?.plant || 'Unknown',
        registeredSubLocation: foundAsset?.subLocation || 'Unknown',
        inspectorName,
        detectedStatus,
        notes,
        gpsCoordinates: '18.7612° N, 73.8421° E',
        discrepancyIdentified: discrepancy
      };

      setMatchedAsset(foundAsset || null);
      setLatestScanResult(newRecord);
      setScanLogs((prev) => [newRecord, ...prev]);

      // Update asset record verification status in state
      if (foundAsset) {
        setAssets((prev) =>
          prev.map((a) =>
            a.id === foundAsset.id
              ? {
                  ...a,
                  verificationStatus: detectedStatus,
                  lastVerifiedDate: new Date().toISOString().split('T')[0]
                }
              : a
          )
        );
      }
    }, 600);
  };

  const handleEscalateToRiskEngine = () => {
    if (!latestScanResult || !matchedAsset) return;

    const newRisk: RiskFinding = {
      id: `RSK-SCAN-${Date.now().toString().slice(-4)}`,
      title: `Verification Anomaly: ${latestScanResult.detectedStatus} - ${matchedAsset.name}`,
      riskType:
        latestScanResult.detectedStatus === 'Wrong Location'
          ? 'Wrong Location'
          : latestScanResult.detectedStatus === 'Suspected Ghost'
          ? 'Ghost Asset'
          : 'Missing Documents',
      severity: latestScanResult.detectedStatus === 'Suspected Ghost' ? 'Critical' : 'High',
      assetId: matchedAsset.id,
      assetName: matchedAsset.name,
      location: latestScanResult.scannedPlant,
      financialExposureINR: matchedAsset.nbvINR,
      explanation: latestScanResult.notes,
      evidence: `Field QR Scan Record ${latestScanResult.id} by ${latestScanResult.inspectorName}`,
      statutoryReference: 'CARO 2020 Clause 3(i)(b)',
      recommendedAction: 'Initiate formal plant controller investigation and inter-unit STN reconciliation.',
      owner: `${latestScanResult.scannedPlant.split(' - ')[0]} Controller`,
      status: 'Detected',
      createdDate: new Date().toISOString().split('T')[0],
      updatedDate: new Date().toISOString().split('T')[0],
      auditTrail: [
        {
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
          user: latestScanResult.inspectorName,
          action: 'Detected via Scanner',
          note: latestScanResult.notes
        }
      ]
    };

    setRisks((prev) => [newRisk, ...prev]);
    setLatestScanResult((prev) => (prev ? { ...prev, exceptionRaised: true } : prev));
  };

  const filteredLogs = scanLogs.filter((log) => {
    if (logFilter === 'Discrepancies') return log.discrepancyIdentified;
    if (logFilter === 'Verified') return log.detectedStatus === 'Verified';
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <QrCode className="w-4 h-4 text-blue-600" />
            <span>CARO 2020 Clause 3(i)(b) Physical Count Protocol</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Physical Verification & Tagging Portal
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time shop-floor barcode/QR tag validation with GPS tagging, automated location mismatch detection, and instant risk escalation.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 text-xs">
          <span className="text-slate-500 font-medium">Total Scans Logged:</span>
          <span className="font-bold text-slate-900 font-mono">{scanLogs.length} Records</span>
        </div>
      </div>

      {/* Main Scanner Section (2 Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Live Verification Scanner (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <Scan className="w-4 h-4 text-blue-600" />
                <span>Shop Floor Scanner Terminal</span>
              </h3>
              <span className="text-[10px] text-emerald-700 font-mono font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                ACTIVE GPS
              </span>
            </div>

            {/* Inspector and Plant Selection */}
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Scanning Plant Location:</label>
                <select
                  value={selectedScanPlant}
                  onChange={(e) => setSelectedScanPlant(e.target.value as PlantLocation)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                >
                  {plants.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Shop Floor Sub-Location / Bay:</label>
                <input
                  type="text"
                  value={selectedSubLocation}
                  onChange={(e) => setSelectedSubLocation(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>

              <div>
                <label className="text-slate-600 block mb-1 font-semibold">Lead Inspector Name:</label>
                <input
                  type="text"
                  value={inspectorName}
                  onChange={(e) => setInspectorName(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>
            </div>

            {/* Viewfinder Box (Professional Dark Terminal Style) */}
            <div className="bg-[#0F172A] border border-slate-700 rounded-xl p-4 text-center space-y-3 relative overflow-hidden shadow-inner text-white">
              <div className="w-full h-40 bg-slate-900/90 rounded-lg border border-dashed border-slate-700 flex flex-col items-center justify-center p-3 relative">
                <div className="w-16 h-16 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center mb-2">
                  <QrCode className="w-10 h-10 text-emerald-400 animate-pulse" />
                </div>
                <span className="text-xs text-slate-200 font-semibold font-mono">
                  {tagInput || 'Point camera at Fixed Asset Tag'}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5">
                  GPS: 18.7612° N, 73.8421° E (Chakan Zone 2)
                </span>

                {/* Laser scanline effect */}
                {isScanning && (
                  <div className="absolute inset-x-0 top-0 h-1 bg-emerald-400 shadow-[0_0_12px_#34d399] animate-bounce" />
                )}
              </div>

              {/* Tag Input Field */}
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="Enter QR/Barcode (e.g. QR-AST-PUN-CNC-0042)"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500"
                />
                <button
                  onClick={() => handleSimulateScan(tagInput)}
                  disabled={isScanning}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 text-white text-xs font-bold rounded-lg transition-all shadow-xs shrink-0"
                >
                  {isScanning ? 'Scanning...' : 'Scan Tag'}
                </button>
              </div>
            </div>

            {/* Quick Demo Scenario Buttons */}
            <div className="space-y-1.5 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Field Audit Test Scenarios:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {quickTestTags.map((item) => (
                  <button
                    key={item.tag}
                    onClick={() => {
                      setTagInput(item.tag);
                      handleSimulateScan(item.tag);
                    }}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-left transition-all font-medium"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>

        {/* Right Column: Scan Evaluation & Exception Action (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {latestScanResult ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
                <div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Verification Result</span>
                  <h3 className="text-lg font-bold text-slate-900">{latestScanResult.assetName}</h3>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center space-x-1.5 ${
                    latestScanResult.detectedStatus === 'Verified'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : latestScanResult.detectedStatus === 'Wrong Location'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    {latestScanResult.detectedStatus === 'Verified' && <CheckCircle2 className="w-3.5 h-3.5" />}
                    {latestScanResult.detectedStatus === 'Wrong Location' && <MapPin className="w-3.5 h-3.5" />}
                    {latestScanResult.detectedStatus !== 'Verified' && latestScanResult.detectedStatus !== 'Wrong Location' && <AlertTriangle className="w-3.5 h-3.5" />}
                    <span>{latestScanResult.detectedStatus}</span>
                  </span>
                </div>
              </div>

              {/* Asset Snapshot Card */}
              {matchedAsset && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="text-slate-500 text-[11px] block font-semibold">Asset Tag ID:</span>
                      <span className="font-mono font-bold text-blue-700">{matchedAsset.id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px] block font-semibold">Gross Cost:</span>
                      <span className="font-mono font-semibold text-slate-900">{formatINR(matchedAsset.costINR, currencyMode)}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px] block font-semibold">Net Book Value:</span>
                      <span className="font-mono font-semibold text-emerald-700">{formatINR(matchedAsset.nbvINR, currencyMode)}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[11px] block font-semibold">Custodian:</span>
                      <span className="text-slate-800 truncate block font-medium">{matchedAsset.custodian}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-slate-200 text-xs">
                    <div className="bg-white border border-slate-200 p-2.5 rounded-lg shadow-2xs">
                      <span className="text-slate-500 text-[11px] block">Registered Plant in Master:</span>
                      <span className="font-semibold text-slate-800">{latestScanResult.registeredPlant}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-2.5 rounded-lg shadow-2xs">
                      <span className="text-slate-500 text-[11px] block">Actual Physical Plant Scanned:</span>
                      <span className={`font-semibold ${
                        latestScanResult.registeredPlant !== latestScanResult.scannedPlant
                          ? 'text-amber-700 font-bold'
                          : 'text-slate-800'
                      }`}>
                        {latestScanResult.scannedPlant}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Inspector Notes & Discrepancy Explanation */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs space-y-2">
                <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                  Auditor Field Observations
                </span>
                <p className="text-slate-700 leading-relaxed">
                  {latestScanResult.notes}
                </p>
                <div className="flex items-center justify-between text-slate-500 pt-1 text-[11px]">
                  <span>Inspector: <strong className="text-slate-700">{latestScanResult.inspectorName}</strong></span>
                  <span className="font-mono">{latestScanResult.timestamp}</span>
                </div>
              </div>

              {/* Action: Discrepancy Escalation */}
              {latestScanResult.discrepancyIdentified ? (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 space-y-3">
                  <div className="flex items-center space-x-2 text-rose-900 text-xs font-bold">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>Control Discrepancy Identified under CARO 2020 Clause 3(i)(b)</span>
                  </div>
                  <p className="text-xs text-rose-800">
                    Physical count reveals a material variance against the Fixed Asset Subledger. Standard audit protocol requires immediate formal exception logging.
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    {latestScanResult.exceptionRaised ? (
                      <span className="text-xs text-emerald-700 font-semibold flex items-center space-x-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Exception already logged in Risk Engine.</span>
                      </span>
                    ) : (
                      <button
                        onClick={handleEscalateToRiskEngine}
                        className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg flex items-center space-x-2 transition-all shadow-xs"
                      >
                        <ShieldAlert className="w-4 h-4" />
                        <span>Escalate to Risk & Exceptions Engine</span>
                      </button>
                    )}

                    {matchedAsset && (
                      <button
                        onClick={() => onNavigateToAsset(matchedAsset.id)}
                        className="text-xs text-slate-600 hover:text-slate-900 underline font-medium"
                      >
                        View Complete Asset Dossier →
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Physical Tag Matched. Subledger and Physical Count are 100% In-Sync.</span>
                  </div>
                  {matchedAsset && (
                    <button
                      onClick={() => onNavigateToAsset(matchedAsset.id)}
                      className="text-emerald-700 hover:text-emerald-900 font-semibold underline"
                    >
                      View Asset Dossier
                    </button>
                  )}
                </div>
              )}

            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 shadow-sm">
              <Scan className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <p className="font-bold text-slate-800">No Tag Scanned Yet</p>
              <p className="text-xs text-slate-500 mt-1">Select a plant and test scenario to begin physical verification.</p>
            </div>
          )}
        </div>

      </div>

      {/* Historical Physical Verification Logs Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Physical Verification Audit Log</h3>
            <p className="text-xs text-slate-500">Chronological ledger of mobile and shop-floor scan events</p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-50 p-1 rounded-lg border border-slate-200 text-xs">
            {(['All', 'Discrepancies', 'Verified'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setLogFilter(filter)}
                className={`px-3 py-1 rounded-md font-medium transition-all ${
                  logFilter === filter
                    ? 'bg-white text-blue-700 shadow-2xs font-bold'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-wider border-b border-slate-200">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Asset ID & Name</th>
                <th className="py-3 px-4">Scanned Location</th>
                <th className="py-3 px-4">Registered Location</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4">Auditor Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                    {log.timestamp}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono font-bold text-slate-900 block">{log.assetId}</span>
                    <span className="text-[11px] text-slate-500 truncate block max-w-xs">{log.assetName}</span>
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    {log.scannedPlant.split(' - ')[0]}
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {log.registeredPlant.split(' - ')[0]}
                  </td>
                  <td className="py-3 px-4 text-center whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      log.detectedStatus === 'Verified'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : log.detectedStatus === 'Wrong Location'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}>
                      {log.detectedStatus}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 max-w-md truncate" title={log.notes}>
                    {log.notes}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
