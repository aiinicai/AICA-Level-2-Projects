import React, { useState, useEffect } from 'react';
import { MasterData, FactorySettings } from '../../types/grn';
import { Truck, Building, FileText, User, Phone, AlertCircle, Check, ChevronDown, Calendar, ShieldAlert } from 'lucide-react';

interface Step1Props {
  formData: {
    supplierName: string;
    supplierQuarry: string;
    challanNumber: string;
    challanDate: string;
    vehicleNumber: string;
    driverName: string;
    driverMobile: string;
    ewayBillNumber: string;
    gateName: string;
    materialType: 'मार्बल ब्लॉक' | 'पत्थर/स्टोन ब्लॉक' | 'अन्य स्लैब/टाइल';
  };
  errors: Record<string, string>;
  masters: MasterData;
  settings: FactorySettings;
  onChange: (field: string, value: any) => void;
  duplicateWarning: {
    isDuplicate: boolean;
    existingGrnNumber?: string;
    existingDate?: string;
  } | null;
  acknowledgedDuplicate: boolean;
  setAcknowledgedDuplicate: (ack: boolean) => void;
}

export const Step1SupplierVehicle: React.FC<Step1Props> = ({
  formData,
  errors,
  masters,
  settings,
  onChange,
  duplicateWarning,
  acknowledgedDuplicate,
  setAcknowledgedDuplicate,
}) => {
  const [showSupplierDropdown, setShowSupplierDropdown] = useState(false);
  const [showVehicleDropdown, setShowVehicleDropdown] = useState(false);

  // Filtered suppliers
  const filteredSuppliers = masters.suppliers.filter(s =>
    !formData.supplierName || s.toLowerCase().includes(formData.supplierName.toLowerCase())
  );

  // Filtered vehicles
  const filteredVehicles = masters.frequentVehicles.filter(v =>
    !formData.vehicleNumber || v.toLowerCase().includes(formData.vehicleNumber.toLowerCase())
  );

  const handleSelectDriver = (driver: { name: string; mobile: string; vehicle: string }) => {
    onChange('driverName', driver.name);
    onChange('driverMobile', driver.mobile);
    if (!formData.vehicleNumber) {
      onChange('vehicleNumber', driver.vehicle);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Duplicate Alert Banner */}
      {duplicateWarning?.isDuplicate && !acknowledgedDuplicate && (
        <div className="bg-amber-100 border-2 border-amber-600 rounded-2xl p-4 text-amber-950 shadow-md">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-6 h-6 text-amber-700 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-extrabold text-base text-amber-900">
                सावधान: संभावित डुप्लिकेट चालान!
              </h4>
              <p className="text-xs sm:text-sm text-amber-900 mt-1">
                इस सप्लायर और चालान नंबर (<strong>{formData.challanNumber}</strong>) की रसीद पहले ही रसीद सं. <strong>{duplicateWarning.existingGrnNumber}</strong> ({duplicateWarning.existingDate}) के रूप में दर्ज हो चुकी है।
              </p>
              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setAcknowledgedDuplicate(true)}
                  className="px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-xs transition"
                >
                  ✓ जांच लिया है, आगे बढ़ने की अनुमति दें
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Material Category Selector */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs">
        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          सामग्री का प्रकार चुनें (Material Category) <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {(['मार्बल ब्लॉक', 'पत्थर/स्टोन ब्लॉक', 'अन्य स्लैब/टाइल'] as const).map((type) => {
            const isSelected = formData.materialType === type;
            return (
              <button
                type="button"
                key={type}
                onClick={() => onChange('materialType', type)}
                className={`py-3 px-3 rounded-xl font-bold text-sm border-2 text-center transition cursor-pointer flex items-center justify-center gap-2 ${
                  isSelected
                    ? 'bg-teal-50 border-teal-600 text-teal-900 shadow-xs'
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                }`}
                style={{ minHeight: '48px' }}
              >
                {isSelected && <Check className="w-4 h-4 text-teal-600" />}
                <span>{type}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Supplier Section */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="font-extrabold text-base text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-2">
          <Building className="w-5 h-5 text-teal-700" />
          <span>सप्लायर / खदान का विवरण</span>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 ml-auto">
            मूल रसीद फील्ड
          </span>
        </h3>

        {/* Supplier Name Input with fast search/picker */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-bold text-slate-700">
              सप्लायर / फर्म का नाम (Supplier Name) <span className="text-red-500">*</span>
            </label>
            <button
              type="button"
              onClick={() => setShowSupplierDropdown(!showSupplierDropdown)}
              className="text-xs font-bold text-teal-700 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>अक्सर आने वाले सप्लायर</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          <input
            type="text"
            value={formData.supplierName || ''}
            onChange={(e) => {
              onChange('supplierName', e.target.value);
              setShowSupplierDropdown(false);
            }}
            placeholder="उदा. मकराना मार्बल माइन्स..."
            className={`w-full p-3.5 rounded-xl border-2 text-base text-slate-900 outline-none transition ${
              errors.supplierName ? 'border-red-500 bg-red-50/30' : 'border-slate-300 focus:border-teal-600'
            }`}
            style={{ minHeight: '48px' }}
          />

          {errors.supplierName && (
            <p className="text-xs text-red-600 font-bold mt-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" /> {errors.supplierName}
            </p>
          )}

          {/* Supplier Dropdown Suggestions */}
          {showSupplierDropdown && (
            <div className="absolute left-0 right-0 top-full mt-1 bg-white border-2 border-teal-600 rounded-xl shadow-xl z-20 max-h-48 overflow-y-auto p-1.5">
              <div className="text-[11px] font-bold text-slate-400 px-2 py-1 uppercase">सप्लायर सूची से चुनें:</div>
              {filteredSuppliers.map((sup) => (
                <button
                  type="button"
                  key={sup}
                  onClick={() => {
                    onChange('supplierName', sup);
                    setShowSupplierDropdown(false);
                  }}
                  className="w-full text-left px-3 py-2.5 rounded-lg text-sm font-semibold hover:bg-teal-50 text-slate-800 transition flex items-center justify-between cursor-pointer"
                >
                  <span>{sup}</span>
                  <Check className="w-4 h-4 text-teal-600 opacity-60" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Supplier Quarry / Range (खदान / रेंज) */}
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1.5">
            खदान / रेंज का नाम (Quarry / Mine Name - यदि उपलब्ध हो)
          </label>
          <input
            type="text"
            value={formData.supplierQuarry || ''}
            onChange={(e) => onChange('supplierQuarry', e.target.value)}
            placeholder="उदा. डूंगरी रेंज / पिपरोली / कुमारी खदान"
            className="w-full p-3.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base text-slate-900 outline-none transition"
            style={{ minHeight: '48px' }}
          />
        </div>
      </div>

      {/* Challan Details */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="font-extrabold text-base text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-2">
          <FileText className="w-5 h-5 text-teal-700" />
          <span>चालान एवं दस्तावेज विवरण</span>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 ml-auto">
            मूल रसीद फील्ड
          </span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Challan Number */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              चालान / डिलीवरी नोट नंबर (Challan No.) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.challanNumber || ''}
              onChange={(e) => onChange('challanNumber', e.target.value.trim())}
              placeholder="उदा. CH-9921"
              className={`w-full p-3.5 rounded-xl border-2 text-base font-mono uppercase text-slate-900 outline-none transition ${
                errors.challanNumber ? 'border-red-500 bg-red-50/30' : 'border-slate-300 focus:border-teal-600'
              }`}
              style={{ minHeight: '48px' }}
            />
            {errors.challanNumber && (
              <p className="text-xs text-red-600 font-bold mt-1 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> {errors.challanNumber}
              </p>
            )}
          </div>

          {/* Challan Date */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              चालान दिनांक (Challan Date) <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={formData.challanDate || ''}
              onChange={(e) => onChange('challanDate', e.target.value)}
              className="w-full p-3.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base text-slate-900 outline-none transition"
              style={{ minHeight: '48px' }}
            />
          </div>
        </div>

        {/* E-way bill (Additional recommended) */}
        <div>
          <label className="block text-xs font-bold text-slate-600 mb-1.5">
            ई-वे बिल नंबर (E-Way Bill No. - वैकल्पिक)
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={formData.ewayBillNumber || ''}
            onChange={(e) => onChange('ewayBillNumber', e.target.value.trim())}
            placeholder="12-अंकों का ई-वे बिल नं. (यदि उपलब्ध हो)"
            className="w-full p-3 rounded-xl border border-slate-300 focus:border-teal-600 text-sm font-mono text-slate-900 outline-none"
            style={{ minHeight: '44px' }}
          />
        </div>
      </div>

      {/* Vehicle & Driver Section */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="font-extrabold text-base text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-2">
          <Truck className="w-5 h-5 text-teal-700" />
          <span>वाहन एवं ड्राइवर विवरण</span>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 ml-auto">
            मूल रसीद फील्ड
          </span>
        </h3>

        {/* Vehicle Number */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-bold text-slate-700">
              गाड़ी नंबर (Vehicle No.) <span className="text-red-500">*</span>
            </label>
            <button
              type="button"
              onClick={() => setShowVehicleDropdown(!showVehicleDropdown)}
              className="text-xs font-bold text-teal-700 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>अक्सर आने वाली गाड़ियां</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          <input
            type="text"
            value={formData.vehicleNumber || ''}
            onChange={(e) => {
              onChange('vehicleNumber', e.target.value.toUpperCase());
              setShowVehicleDropdown(false);
            }}
            placeholder="उदा. RJ-01-GA-4589"
            className={`w-full p-3.5 rounded-xl border-2 text-lg font-mono font-bold uppercase text-slate-900 outline-none transition ${
              errors.vehicleNumber ? 'border-red-500 bg-red-50/30' : 'border-slate-300 focus:border-teal-600'
            }`}
            style={{ minHeight: '48px' }}
          />

          {errors.vehicleNumber && (
            <p className="text-xs text-red-600 font-bold mt-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" /> {errors.vehicleNumber}
            </p>
          )}

          {showVehicleDropdown && (
            <div className="absolute left-0 right-0 top-full mt-1 bg-white border-2 border-teal-600 rounded-xl shadow-xl z-20 max-h-48 overflow-y-auto p-1.5">
              <div className="text-[11px] font-bold text-slate-400 px-2 py-1 uppercase">वाहन सूची से चुनें:</div>
              {filteredVehicles.map((v) => (
                <button
                  type="button"
                  key={v}
                  onClick={() => {
                    onChange('vehicleNumber', v);
                    setShowVehicleDropdown(false);
                  }}
                  className="w-full text-left px-3 py-2.5 rounded-lg text-sm font-mono font-bold hover:bg-teal-50 text-slate-800 transition flex items-center justify-between cursor-pointer"
                >
                  <span>{v}</span>
                  <Check className="w-4 h-4 text-teal-600 opacity-60" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Driver Name & Mobile */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              ड्राइवर का नाम (Driver Name) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.driverName || ''}
              onChange={(e) => onChange('driverName', e.target.value)}
              placeholder="उदा. रामनिवास गुर्जर"
              className={`w-full p-3.5 rounded-xl border-2 text-base text-slate-900 outline-none transition ${
                errors.driverName ? 'border-red-500 bg-red-50/30' : 'border-slate-300 focus:border-teal-600'
              }`}
              style={{ minHeight: '48px' }}
            />
            {errors.driverName && (
              <p className="text-xs text-red-600 font-bold mt-1 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> {errors.driverName}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              ड्राइवर मोबाइल नंबर (Mobile No. - वैकल्पिक)
            </label>
            <input
              type="tel"
              inputMode="tel"
              maxLength={10}
              value={formData.driverMobile || ''}
              onChange={(e) => onChange('driverMobile', e.target.value.replace(/\D/g, ''))}
              placeholder="10-अंकों का मोबाइल नंबर"
              className="w-full p-3.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono text-slate-900 outline-none transition"
              style={{ minHeight: '48px' }}
            />
          </div>
        </div>

        {/* Quick select frequent drivers */}
        {masters.frequentDrivers.length > 0 && (
          <div>
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
              या परिचित ड्राइवर चुनें:
            </div>
            <div className="flex flex-wrap gap-1.5">
              {masters.frequentDrivers.map((d) => (
                <button
                  type="button"
                  key={d.name}
                  onClick={() => handleSelectDriver(d)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 border border-slate-200 text-xs font-semibold text-slate-700 hover:text-teal-800 transition cursor-pointer"
                >
                  {d.name} ({d.vehicle})
                </button>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Gate Selection */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs">
        <label className="block text-xs font-bold text-slate-700 mb-1.5">
          गेट का नाम (Gate) <span className="text-red-500">*</span>
        </label>
        <select
          value={formData.gateName || ''}
          onChange={(e) => onChange('gateName', e.target.value)}
          className="w-full p-3.5 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base text-slate-900 outline-none transition bg-white"
          style={{ minHeight: '48px' }}
        >
          {settings.gates.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>

    </div>
  );
};
