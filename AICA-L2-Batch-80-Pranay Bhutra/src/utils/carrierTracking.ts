export interface CarrierInfo {
  name: string;
  trackingUrl?: (trackingNumber: string) => string;
  portalUrl?: string;
  helpline?: string;
  isOnlineTrackable: boolean;
}

export const CARRIER_REGISTRY: Record<string, CarrierInfo> = {
  'Blue Dart Express': {
    name: 'Blue Dart Express',
    trackingUrl: (awb: string) => `https://www.bluedart.com/tracking?trackNumber=${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.bluedart.com',
    helpline: '1860 233 1234',
    isOnlineTrackable: true,
  },
  'DTDC Courier': {
    name: 'DTDC Courier',
    trackingUrl: (awb: string) => `https://www.dtdc.in/tracking/tracking_results.asp?trNum=${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.dtdc.in',
    helpline: '080-25365032',
    isOnlineTrackable: true,
  },
  'DHL Express': {
    name: 'DHL Express',
    trackingUrl: (awb: string) => `https://www.dhl.com/en/express/tracking.html?AWB=${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.dhl.com',
    helpline: '1800 111 345',
    isOnlineTrackable: true,
  },
  'FedEx India': {
    name: 'FedEx India',
    trackingUrl: (awb: string) => `https://www.fedex.com/fedextrack/?trknbr=${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.fedex.com',
    helpline: '1800 209 6161',
    isOnlineTrackable: true,
  },
  'India Post - Speed Post': {
    name: 'India Post - Speed Post',
    trackingUrl: (awb: string) => `https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx`,
    portalUrl: 'https://www.indiapost.gov.in',
    helpline: '1800 266 6868',
    isOnlineTrackable: true,
  },
  'Professional Couriers': {
    name: 'Professional Couriers',
    trackingUrl: (awb: string) => `https://www.tpcindia.com/track.aspx?awb=${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.tpcindia.com',
    helpline: '022-27813309',
    isOnlineTrackable: true,
  },
  'Delhivery': {
    name: 'Delhivery',
    trackingUrl: (awb: string) => `https://www.delhivery.com/track/package/${encodeURIComponent(awb)}`,
    portalUrl: 'https://www.delhivery.com',
    helpline: '0124 6719500',
    isOnlineTrackable: true,
  },
  'Direct Office Peon / Hand Delivery': {
    name: 'Direct Office Peon / Hand Delivery',
    isOnlineTrackable: false,
    helpline: 'Firm Internal Admin Desk (Ext. 102)'
  },
  'Porter / Dunzo Express': {
    name: 'Porter / Dunzo Express',
    portalUrl: 'https://porter.in',
    isOnlineTrackable: false,
    helpline: 'Refer to booking app order history'
  },
  'Others (Custom Carrier)': {
    name: 'Others (Custom Carrier)',
    isOnlineTrackable: false,
    helpline: 'Contact local dispatch desk / agent'
  }
};

export function getCarrierTracking(carrierName: string, trackingNumber: string): {
  isTrackable: boolean;
  trackingUrl?: string;
  carrierName: string;
  portalUrl?: string;
  helpline?: string;
} {
  // Find matching carrier in registry
  const matchKey = Object.keys(CARRIER_REGISTRY).find(
    (key) => key.toLowerCase() === carrierName.toLowerCase() || carrierName.toLowerCase().includes(key.toLowerCase())
  );

  const carrier = matchKey ? CARRIER_REGISTRY[matchKey] : null;

  if (carrier && carrier.isOnlineTrackable && carrier.trackingUrl) {
    return {
      isTrackable: true,
      trackingUrl: carrier.trackingUrl(trackingNumber),
      carrierName: carrier.name,
      portalUrl: carrier.portalUrl,
      helpline: carrier.helpline,
    };
  }

  return {
    isTrackable: false,
    carrierName: carrierName || 'Custom Carrier',
    portalUrl: carrier?.portalUrl,
    helpline: carrier?.helpline || 'Dispatch Reception (Ext 102)',
  };
}
