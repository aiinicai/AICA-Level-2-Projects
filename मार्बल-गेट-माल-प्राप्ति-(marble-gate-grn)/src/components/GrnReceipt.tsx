import React from 'react';
import { GoodsReceiptNote, FactorySettings, UserAccount } from '../types/grn';
import { Printer, Download, Share2, ArrowLeft, CheckCircle2, AlertTriangle, Building2, Edit3, ShieldAlert } from 'lucide-react';

interface GrnReceiptProps {
  grn: GoodsReceiptNote;
  settings: FactorySettings;
  currentUser: UserAccount;
  onBack: () => void;
  onEdit?: (grn: GoodsReceiptNote) => void;
}

export const GrnReceipt: React.FC<GrnReceiptProps> = ({
  grn,
  settings,
  currentUser,
  onBack,
  onEdit,
}) => {

  const handlePrint = () => {
    window.print();
  };

  const handleShare = async () => {
    const textSummary = `*${settings.factoryName}*\n${settings.receiptTitle}\nरसीद सं: ${grn.grnNumber}\nदिनांक: ${grn.date} ${grn.time}\nसप्लायर: ${grn.supplierName}\nगाड़ी नं: ${grn.vehicleNumber}\nचालान नं: ${grn.challanNumber}\nकुल ब्लॉक: ${grn.totalBlocks} (${grn.totalPieces} टुकड़े)\nअनुमानित आयतन: ${grn.totalVolumeEstimateCft} CFT\nस्थिति: ${grn.status}`;

    if (navigator.share) {
      try {
        await navigator.share({
          title: `GRN - ${grn.grnNumber}`,
          text: textSummary,
        });
      } catch (err) {
        console.log('Share dismissed:', err);
      }
    } else {
      // Fallback: Copy to clipboard
      try {
        await navigator.clipboard.writeText(textSummary);
        alert('रसीद का संक्षिप्त विवरण कॉपी हो गया है। आप इसे व्हाट्सएप पर भेज सकते हैं।');
      } catch {
        alert(textSummary);
      }
    }
  };

  const handleDownloadFile = () => {
    // Generate self-contained printable HTML document with embedded CSS and Hindi font
    const receiptHtml = `<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8">
  <title>${grn.grnNumber} - ${settings.receiptTitle}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700;900&display=swap" rel="stylesheet">
  <style>
    @page { size: A4 portrait; margin: 12mm 10mm; }
    body { font-family: 'Noto Sans Devanagari', Arial, sans-serif; margin: 0; padding: 20px; color: #000; font-size: 11pt; line-height: 1.35; }
    .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; }
    .factory-name { font-size: 18pt; font-weight: 900; margin: 0; }
    .title-box { display: inline-block; background: #000; color: #fff; padding: 4px 14px; font-weight: 800; font-size: 11pt; margin-top: 6px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; font-size: 10pt; }
    .info-box { border: 1px solid #000; padding: 6px 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9.5pt; }
    th, td { border: 1px solid #000; padding: 5px 6px; text-align: left; }
    th { background-color: #f0f0f0; }
    .text-center { text-align: center; }
    .text-right { text-align: right; }
    .declaration { border: 1px solid #000; padding: 8px; margin-top: 14px; font-size: 9pt; background: #fafafa; }
    .signatures { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 35px; text-align: center; font-size: 9pt; }
    .sig-space { border-top: 1px dotted #000; padding-top: 4px; font-weight: bold; }
    .watermark { color: #dc2626; font-size: 16pt; font-weight: 900; text-align: center; border: 2px dashed #dc2626; padding: 4px; margin-bottom: 8px; }
  </style>
</head>
<body>
  ${grn.isProvisional ? '<div class="watermark">⚠ अस्थायी रसीद — सिंक बाकी (PROVISIONAL GRN)</div>' : ''}
  <div class="header">
    <div style="font-size: 9pt; text-transform: uppercase;">${settings.factoryTagline}</div>
    <h1 class="factory-name">${settings.factoryName}</h1>
    <div style="font-size: 9pt;">${settings.factoryAddress} | फोन: ${settings.factoryPhone}</div>
    <div style="font-size: 9pt; font-weight: bold;">GSTIN: ${settings.factoryGstin}</div>
    <div><span class="title-box">${settings.receiptTitle}</span></div>
  </div>

  <div class="info-grid">
    <div class="info-box">
      <div><strong>रसीद सं. (GRN No):</strong> ${grn.grnNumber}</div>
      <div><strong>दिनांक व समय:</strong> ${grn.date} ${grn.time}</div>
      <div><strong>गेट:</strong> ${grn.gateName}</div>
      <div><strong>प्राप्तकर्ता:</strong> ${grn.receiverName} (${grn.receiverRole})</div>
    </div>
    <div class="info-box">
      <div><strong>सप्लायर:</strong> ${grn.supplierName} ${grn.supplierQuarry ? `(${grn.supplierQuarry})` : ''}</div>
      <div><strong>चालान सं. व दिनांक:</strong> ${grn.challanNumber} (${grn.challanDate})</div>
      <div><strong>गाड़ी नंबर:</strong> ${grn.vehicleNumber}</div>
      <div><strong>ड्राइवर:</strong> ${grn.driverName} ${grn.driverMobile ? `(${grn.driverMobile})` : ''}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th class="text-center" style="width: 30px;">क्र.</th>
        <th>ब्लॉक नंबर / मार्क</th>
        <th>किस्म (Variety)</th>
        <th class="text-center">टुकड़े</th>
        <th class="text-center">नाप (L × W × H)</th>
        <th class="text-right">अनुमानित आयतन (CFT)</th>
        <th class="text-center">स्थिति</th>
      </tr>
    </thead>
    <tbody>
      ${grn.blocks.map((b, i) => `
        <tr>
          <td class="text-center">${i + 1}</td>
          <td><strong>${b.blockNumber}</strong></td>
          <td>${b.variety}</td>
          <td class="text-center">${b.pieces || 1}</td>
          <td class="text-center">${b.length} × ${b.width} × ${b.height} ${b.unit.split(' ')[0]}</td>
          <td class="text-right"><strong>${Number(b.estimatedVolume).toFixed(2)}</strong></td>
          <td class="text-center">${b.condition}</td>
        </tr>
      `).join('')}
    </tbody>
    <tfoot>
      <tr style="font-weight: bold; background: #f5f5f5;">
        <td colspan="3" class="text-right">कुल योग (Total):</td>
        <td class="text-center">${grn.totalPieces}</td>
        <td class="text-center">-</td>
        <td class="text-right">${Number(grn.totalVolumeEstimateCft).toFixed(2)} CFT</td>
        <td></td>
      </tr>
    </tfoot>
  </table>

  ${grn.weighbridge?.enabled ? `
    <div style="border: 1px solid #000; padding: 6px 10px; margin-top: 10px; font-size: 9.5pt;">
      <strong>धर्मकांटा वजन पर्ची:</strong> पर्ची सं. ${grn.weighbridge.slipNumber || '-'} | सकल: ${grn.weighbridge.grossWeight} ${grn.weighbridge.unit.split(' ')[0]} | खाली: ${grn.weighbridge.tareWeight} ${grn.weighbridge.unit.split(' ')[0]} | <strong>शुद्ध वजन: ${grn.weighbridge.netWeight} ${grn.weighbridge.unit.split(' ')[0]}</strong>
    </div>
  ` : ''}

  ${grn.generalRemarks ? `
    <div style="margin-top: 8px; font-size: 9pt;"><strong>टिप्पणी:</strong> ${grn.generalRemarks}</div>
  ` : ''}

  <div class="declaration">
    <strong>घोषणा (Declaration):</strong> ${settings.declarationText}
  </div>

  <div class="signatures">
    <div>
      <div style="height: 40px;">${grn.receiverSignature ? `<img src="${grn.receiverSignature}" style="max-height: 40px;" />` : ''}</div>
      <div class="sig-space">प्राप्तकर्ता हस्ताक्षर<br><span style="font-size: 8pt; font-weight: normal;">(${grn.receiverName})</span></div>
    </div>
    <div>
      <div style="height: 40px;">${grn.driverSignature ? `<img src="${grn.driverSignature}" style="max-height: 40px;" />` : ''}</div>
      <div class="sig-space">वाहन चालक हस्ताक्षर<br><span style="font-size: 8pt; font-weight: normal;">(${grn.driverName})</span></div>
    </div>
    <div>
      <div style="height: 40px;"></div>
      <div class="sig-space">अधिकृत प्रबंधक हस्ताक्षर<br><span style="font-size: 8pt; font-weight: normal;">(मुहर सहित)</span></div>
    </div>
  </div>
</body>
</html>`;

    const blob = new Blob([receiptHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${grn.grnNumber}-${grn.supplierName}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      
      {/* Top Action Bar (Hidden in Print) */}
      <div className="no-print bg-white rounded-3xl p-4 sm:p-5 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-extrabold text-sm rounded-xl transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>वापस जाएं</span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          {currentUser.role === 'admin' && onEdit && grn.status !== 'रद्द' && (
            <button
              onClick={() => onEdit(grn)}
              className="flex items-center gap-1.5 px-3 py-2.5 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-300 font-bold text-xs rounded-xl transition cursor-pointer"
              title="रसीद संशोधित करें (संशोधन इतिहास सुरक्षित रहेगा)"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>संशोधन करें</span>
            </button>
          )}

          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl transition cursor-pointer"
            title="साझा करें"
          >
            <Share2 className="w-4 h-4 text-teal-700" />
            <span>साझा करें</span>
          </button>

          <button
            onClick={handleDownloadFile}
            className="flex items-center gap-1.5 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs transition cursor-pointer"
            title="रसीद फाइल डाउनलोड करें"
          >
            <Download className="w-4 h-4 text-amber-300" />
            <span>PDF / फाइल डाउनलोड</span>
          </button>

          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-black text-sm rounded-xl shadow-md shadow-teal-900/20 transition active:scale-95 cursor-pointer"
            title="प्रिंट करें"
          >
            <Printer className="w-4 h-4 text-amber-300" />
            <span>प्रिंट करें (A4)</span>
          </button>
        </div>
      </div>

      {/* Provisional Watermark Warning (if offline) */}
      {grn.isProvisional && (
        <div className="no-print bg-amber-50 border-2 border-amber-500 rounded-2xl p-4 text-amber-950 flex items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 text-amber-600 shrink-0" />
            <div>
              <div className="font-extrabold text-sm sm:text-base">
                अस्थायी रसीद — सिंक बाकी ({grn.grnNumber})
              </div>
              <div className="text-xs text-amber-800">
                जैसे ही फ़ोन इंटरनेट से जुड़ेगा, इसे स्थायी GRN नंबर स्वतः आवंटित कर दिया जाएगा।
              </div>
            </div>
          </div>
          <span className="text-xs font-bold px-2.5 py-1 bg-amber-500 text-slate-950 rounded-full">
            इस डिवाइस पर सुरक्षित
          </span>
        </div>
      )}

      {/* Cancellation Banner if Cancelled */}
      {grn.status === 'रद्द' && (
        <div className="bg-red-50 border-2 border-red-500 rounded-2xl p-4 text-red-950 shadow-md">
          <div className="flex items-center gap-2 font-black text-base text-red-900">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span>यह रसीद रद्द (CANCELLED) की जा चुकी है</span>
          </div>
          <p className="text-xs text-red-800 mt-1">
            <strong>रद्द करने का कारण:</strong> {grn.cancellationReason || 'प्रबंधक द्वारा रद्द'} | <strong>रद्दकर्ता:</strong> {grn.cancelledBy} ({grn.cancelledAt ? new Date(grn.cancelledAt).toLocaleString('hi-IN') : ''})
          </p>
        </div>
      )}

      {/* Revision Notice if Revised */}
      {grn.revisions && grn.revisions.length > 0 && (
        <div className="bg-purple-50 border border-purple-300 rounded-2xl p-3 text-purple-950 text-xs">
          <strong>संशोधन सूचना:</strong> यह रसीद <strong>संशोधन #{grn.revisions.length}</strong> है। पिछला सुधार: {grn.revisions[grn.revisions.length - 1].reason} (द्वारा: {grn.revisions[grn.revisions.length - 1].revisedBy})
        </div>
      )}

      {/* Official A4 Printable Receipt Document */}
      <div className="print-container bg-white rounded-3xl border-2 border-slate-300 p-6 sm:p-10 shadow-xl text-slate-900 space-y-6">
        
        {/* Printable Watermark for Provisional Receipts */}
        {grn.isProvisional && (
          <div className="border-2 border-dashed border-red-600 bg-red-50 text-red-700 font-black text-center py-1.5 px-3 rounded-lg text-xs tracking-wider uppercase">
            ⚠ अस्थायी रसीद — सिंक बाकी (PROVISIONAL GRN — PENDING SERVER SYNC)
          </div>
        )}

        {/* Factory Header */}
        <div className="text-center border-b-2 border-slate-900 pb-4">
          <div className="text-[11px] font-bold text-teal-800 tracking-widest uppercase">
            {settings.factoryTagline}
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 mt-0.5 tracking-tight">
            {settings.factoryName}
          </h1>
          <div className="text-xs text-slate-600 mt-1">
            {settings.factoryAddress} | फोन: {settings.factoryPhone}
          </div>
          <div className="text-xs font-mono font-bold text-slate-800 mt-0.5">
            GSTIN: {settings.factoryGstin}
          </div>

          <div className="mt-3 inline-block bg-slate-900 text-white font-black px-5 py-1.5 rounded-lg text-sm sm:text-base uppercase tracking-wide">
            {settings.receiptTitle}
          </div>
        </div>

        {/* GRN Meta & Timing Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-2xl border border-slate-200 text-xs">
          <div>
            <span className="text-slate-500 block">रसीद नंबर (GRN No):</span>
            <span className="font-mono font-black text-base text-teal-900">{grn.grnNumber}</span>
          </div>
          <div>
            <span className="text-slate-500 block">दिनांक व समय:</span>
            <span className="font-bold text-slate-900">{grn.date} | {grn.time}</span>
          </div>
          <div>
            <span className="text-slate-500 block">गेट का नाम:</span>
            <span className="font-bold text-slate-900">{grn.gateName}</span>
          </div>
          <div>
            <span className="text-slate-500 block">प्राप्तकर्ता (Received By):</span>
            <span className="font-bold text-slate-900">{grn.receiverName}</span>
          </div>
        </div>

        {/* Supplier & Transport Box */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="border border-slate-300 rounded-2xl p-3.5 space-y-1.5 bg-slate-50/40">
            <div className="font-bold text-slate-900 border-b border-slate-200 pb-1">
              आपूर्तिकर्ता विवरण (Supplier Details):
            </div>
            <div><strong>सप्लायर फर्म:</strong> {grn.supplierName}</div>
            {grn.supplierQuarry && <div><strong>खदान / रेंज:</strong> {grn.supplierQuarry}</div>}
            <div><strong>चालान सं.:</strong> <span className="font-mono font-bold">{grn.challanNumber}</span></div>
            <div><strong>चालान दिनांक:</strong> {grn.challanDate}</div>
            {grn.ewayBillNumber && <div><strong>ई-वे बिल नं.:</strong> <span className="font-mono">{grn.ewayBillNumber}</span></div>}
          </div>

          <div className="border border-slate-300 rounded-2xl p-3.5 space-y-1.5 bg-slate-50/40">
            <div className="font-bold text-slate-900 border-b border-slate-200 pb-1">
              वाहन एवं चालक विवरण (Vehicle & Transport):
            </div>
            <div><strong>गाड़ी नंबर:</strong> <span className="font-mono font-black text-slate-900 text-sm">{grn.vehicleNumber}</span></div>
            <div><strong>चालक (Driver):</strong> {grn.driverName}</div>
            {grn.driverMobile && <div><strong>मोबाइल नंबर:</strong> <span className="font-mono">{grn.driverMobile}</span></div>}
            <div><strong>सामग्री श्रेणी:</strong> {grn.materialType}</div>
          </div>
        </div>

        {/* Material & Blocks Table */}
        <div>
          <h3 className="font-black text-sm text-slate-900 mb-2">
            प्राप्त मार्बल एवं स्टोन ब्लॉक विवरण:
          </h3>
          <div className="overflow-x-auto">
            <table className="print-table w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-800 text-white font-bold">
                  <th className="p-2 border border-slate-700 text-center" style={{ width: '35px' }}>क्र.</th>
                  <th className="p-2 border border-slate-700">ब्लॉक नंबर / मार्क</th>
                  <th className="p-2 border border-slate-700">किस्म (Variety)</th>
                  <th className="p-2 border border-slate-700 text-center">टुकड़े</th>
                  <th className="p-2 border border-slate-700 text-center">नाप (L × W × H)</th>
                  <th className="p-2 border border-slate-700 text-right">अनुमानित आयतन</th>
                  <th className="p-2 border border-slate-700 text-center">स्थिति</th>
                </tr>
              </thead>
              <tbody>
                {grn.blocks.map((b, idx) => (
                  <tr key={b.id || idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                    <td className="p-2 border border-slate-300 text-center font-bold">{idx + 1}</td>
                    <td className="p-2 border border-slate-300 font-mono font-bold text-slate-900">{b.blockNumber}</td>
                    <td className="p-2 border border-slate-300">{b.variety}</td>
                    <td className="p-2 border border-slate-300 text-center font-bold">{b.pieces || 1}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono">
                      {b.length} × {b.width} × {b.height} {b.unit ? b.unit.split(' ')[0] : 'इंच'}
                    </td>
                    <td className="p-2 border border-slate-300 text-right font-mono font-bold text-slate-900">
                      {Number(b.estimatedVolume).toFixed(2)} CFT
                    </td>
                    <td className="p-2 border border-slate-300 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        b.condition === 'ठीक' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {b.condition}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-black text-slate-900 border-t-2 border-slate-800">
                  <td colSpan={3} className="p-2 border border-slate-300 text-right">कुल योग (Total Summary):</td>
                  <td className="p-2 border border-slate-300 text-center">{grn.totalPieces}</td>
                  <td className="p-2 border border-slate-300 text-center">-</td>
                  <td className="p-2 border border-slate-300 text-right text-teal-900 font-mono font-black">
                    {Number(grn.totalVolumeEstimateCft).toFixed(2)} CFT
                  </td>
                  <td className="p-2 border border-slate-300"></td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div className="text-[10px] text-slate-500 mt-1 italic">
            * नोट: आयतन गणना घनाकार (Length × Width × Height) पर आधारित अनुमानित माप है।
          </div>
        </div>

        {/* Weighbridge Record */}
        {grn.weighbridge?.enabled && (
          <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-300 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div>
              <span className="font-bold text-slate-900">धर्मकांटा पर्ची: </span>
              <span>पर्ची सं.: {grn.weighbridge.slipNumber || '-'} ({grn.weighbridge.weighbridgeName || 'धर्मकांटा'})</span>
            </div>
            <div className="flex gap-4 font-mono font-semibold">
              <span>सकल वजन: <strong>{grn.weighbridge.grossWeight} {grn.weighbridge.unit.split(' ')[0]}</strong></span>
              <span>खाली गाड़ी: <strong>{grn.weighbridge.tareWeight} {grn.weighbridge.unit.split(' ')[0]}</strong></span>
              <span className="text-teal-950 font-black bg-teal-100 px-2.5 py-0.5 rounded">
                शुद्ध वजन (Net): {grn.weighbridge.netWeight} {grn.weighbridge.unit.split(' ')[0]}
              </span>
            </div>
          </div>
        )}

        {/* Photos Preview (Screen only) */}
        {grn.photos && Object.values(grn.photos).some(Boolean) && (
          <div className="no-print space-y-2">
            <h4 className="font-bold text-xs text-slate-700">संलग्न फोटो:</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {grn.photos.vehicle && (
                <div>
                  <img src={grn.photos.vehicle} alt="गाड़ी" className="w-full h-24 object-cover rounded-xl border border-slate-200" />
                  <span className="text-[10px] text-slate-500 block text-center mt-0.5">गाड़ी फोटो</span>
                </div>
              )}
              {grn.photos.blocks && (
                <div>
                  <img src={grn.photos.blocks} alt="ब्लॉक" className="w-full h-24 object-cover rounded-xl border border-slate-200" />
                  <span className="text-[10px] text-slate-500 block text-center mt-0.5">ब्लॉक फोटो</span>
                </div>
              )}
              {grn.photos.challan && (
                <div>
                  <img src={grn.photos.challan} alt="चालान" className="w-full h-24 object-cover rounded-xl border border-slate-200" />
                  <span className="text-[10px] text-slate-500 block text-center mt-0.5">चालान पर्ची</span>
                </div>
              )}
              {grn.photos.weighbridgeSlip && (
                <div>
                  <img src={grn.photos.weighbridgeSlip} alt="कांटा पर्ची" className="w-full h-24 object-cover rounded-xl border border-slate-200" />
                  <span className="text-[10px] text-slate-500 block text-center mt-0.5">कांटा पर्ची</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Remarks */}
        {grn.generalRemarks && (
          <div className="text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
            <strong>विशेष टिप्पणी:</strong> {grn.generalRemarks}
          </div>
        )}

        {/* Declaration Statement */}
        <div className="bg-amber-50/50 border border-amber-300 p-3 rounded-xl text-xs text-amber-950">
          <strong>घोषणा (Declaration):</strong> {settings.declarationText}
        </div>

        {/* Signatures Row */}
        <div className="page-break-avoid grid grid-cols-3 gap-4 pt-4 border-t-2 border-slate-800 text-xs text-center">
          <div className="space-y-1">
            <div className="h-16 border border-slate-200 rounded-xl bg-slate-50 flex items-center justify-center p-1">
              {grn.receiverSignature ? (
                <img src={grn.receiverSignature} alt="साइन" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-slate-400 italic">हस्ताक्षर</span>
              )}
            </div>
            <div className="font-bold text-slate-800">गेट कर्मचारी / प्राप्तकर्ता</div>
            <div className="text-[10px] text-slate-500">({grn.receiverName})</div>
          </div>

          <div className="space-y-1">
            <div className="h-16 border border-slate-200 rounded-xl bg-slate-50 flex items-center justify-center p-1">
              {grn.driverSignature ? (
                <img src={grn.driverSignature} alt="ड्राइवर साइन" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-slate-400 italic">ड्राइवर हस्ताक्षर</span>
              )}
            </div>
            <div className="font-bold text-slate-800">वाहन चालक (Driver)</div>
            <div className="text-[10px] text-slate-500">({grn.driverName})</div>
          </div>

          <div className="space-y-1">
            <div className="h-16 border border-dashed border-slate-300 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400 italic text-[11px]">
              सील / मुहर
            </div>
            <div className="font-bold text-slate-800">अधिकृत प्रबंधक हस्ताक्षर</div>
            <div className="text-[10px] text-slate-500">(फैक्ट्री मुहर सहित)</div>
          </div>
        </div>

        {/* Footer Audit Info */}
        <div className="border-t border-slate-200 pt-3 flex flex-wrap items-center justify-between text-[10px] text-slate-500">
          <div>
            रसीद निर्माण: {grn.createdAt ? new Date(grn.createdAt).toLocaleString('hi-IN') : `${grn.date} ${grn.time}`} | ऑपरेटर: {grn.createdBy || grn.receiverName}
          </div>
          <div>
            स्थिति: <strong className="text-slate-700">{grn.status}</strong> | सिंक: <strong className="text-slate-700">{grn.syncStatus}</strong>
          </div>
        </div>

      </div>

    </div>
  );
};
