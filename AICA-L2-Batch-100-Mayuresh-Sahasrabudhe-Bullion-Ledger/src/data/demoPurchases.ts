import { Purchase } from '../types';

export const DEMO_PURCHASES: Purchase[] = [
  {
    id: 'DEMO-2021-GLD-01',
    purchaseDate: '2021-04-16',
    seller: 'Tanishq Jewellers',
    invoiceNumber: 'TAN-009214',
    metal: 'GOLD',
    form: 'COIN',
    purity: 999,
    weightGrams: 10.0,
    purchaseRate: 4689.10, // ~46,891/10g
    taxesPaid: 1406.73, // 3% GST on bullion
    otherCharges: 450.00, // coin minting charge
    bullionValue: 46891.00,
    investedAmount: 48747.73,
    notes: 'Akshaya Tritiya MMTC-PAMP minted Lotus Coin with tamper-evident certicard.',
    isDemo: true,
    deleted: false,
    createdAt: '2021-04-16T11:30:00.000Z',
    updatedAt: '2021-04-16T11:30:00.000Z'
  },
  {
    id: 'DEMO-2022-GLD-02',
    purchaseDate: '2022-10-21',
    seller: 'Zaveri Bazaar Bullion Mart',
    invoiceNumber: 'ZAV-104882',
    metal: 'GOLD',
    form: 'VEDHANI',
    purity: 995,
    weightGrams: 20.0,
    purchaseRate: 4293.60, // ~42,936/10g
    taxesPaid: 2576.16,
    otherCharges: 0,
    bullionValue: 85872.00,
    investedAmount: 88448.16,
    notes: 'Dhanteras Vedhani hallmarked 995 bullion ring for long-term holding.',
    isDemo: true,
    deleted: false,
    createdAt: '2022-10-21T16:45:00.000Z',
    updatedAt: '2022-10-21T16:45:00.000Z'
  },
  {
    id: 'DEMO-2023-SLV-01',
    purchaseDate: '2023-03-10',
    seller: 'BRPL Bullion Refiners',
    invoiceNumber: 'BRPL-SLV-8821',
    metal: 'SILVER',
    form: 'BAR',
    purity: 999,
    weightGrams: 1000.0, // 1 Kg
    purchaseRate: 61.584, // ~61,584/kg
    taxesPaid: 1847.52,
    otherCharges: 250.00,
    bullionValue: 61584.00,
    investedAmount: 63681.52,
    notes: 'Serialized 1 Kilogram 999 Fine Silver Cast Bar with refinery certificate.',
    isDemo: true,
    deleted: false,
    createdAt: '2023-03-10T14:15:00.000Z',
    updatedAt: '2023-03-10T14:15:00.000Z'
  },
  {
    id: 'DEMO-2024-GLD-03',
    purchaseDate: '2024-02-15',
    seller: 'Malabar Gold & Diamonds',
    invoiceNumber: 'MGD-2024-771',
    metal: 'GOLD',
    form: 'BAR',
    purity: 999,
    weightGrams: 50.0,
    purchaseRate: 6131.00, // ~61,310/10g
    taxesPaid: 9196.50,
    otherCharges: 750.00,
    bullionValue: 306550.00,
    investedAmount: 316496.50,
    notes: '50g Fine Gold Minted Bar 999 purity with refinery assay.',
    isDemo: true,
    deleted: false,
    createdAt: '2024-02-15T18:00:00.000Z',
    updatedAt: '2024-02-15T18:00:00.000Z'
  },
  {
    id: 'DEMO-2024-SLV-02',
    purchaseDate: '2024-07-25',
    seller: 'Kundan Bullion',
    invoiceNumber: 'KUN-99201',
    metal: 'SILVER',
    form: 'COIN',
    purity: 999,
    weightGrams: 250.0,
    purchaseRate: 81.476, // ~81,476/kg
    taxesPaid: 611.07,
    otherCharges: 200.00,
    bullionValue: 20369.00,
    investedAmount: 21180.07,
    notes: '5 x 50g Silver Coins set in protective capsules.',
    isDemo: true,
    deleted: false,
    createdAt: '2024-07-25T12:00:00.000Z',
    updatedAt: '2024-07-25T12:00:00.000Z'
  }
];
