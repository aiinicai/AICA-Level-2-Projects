import React from 'react';
import { CheckCircle, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const TierCard = ({ tier, currentPlan }) => {
  const navigate = useNavigate();

  const handleUpgrade = () => {
    navigate('/payment');
  };

  return (
    <motion.div
      whileHover={{ y: -5 }}
      className={`bg-dark-card border rounded-2xl p-8 flex flex-col h-full ${tier.highlight ? 'border-accent-blue' : 'border-dark-border'}`}>
      <div className="flex-grow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-2xl font-bold text-text-primary">{tier.name}</h3>
          {tier.highlight && (
            <span className="bg-accent-blue/20 text-accent-blue text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
              <Zap size={12} />
              Most Popular
            </span>
          )}
        </div>
        <p className="text-4xl font-bold mb-2">{tier.price}</p>
        <p className="text-text-secondary mb-8 h-10">{tier.description}</p>
        <ul className="space-y-4">
          {tier.features.map((feature, index) => (
            <li key={index} className="flex items-start">
              <CheckCircle className="w-5 h-5 text-accent-green mr-3 mt-1 flex-shrink-0" />
              <span className="text-text-secondary">{feature}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-10">
        {tier.name.toLowerCase() === currentPlan ? (
          <button className="w-full bg-gray-100 text-gray-700 font-bold py-3 rounded-lg shadow hover:bg-gray-200 transition-colors cursor-default">
            Your Current Plan
          </button>
        ) : (
          <button
            onClick={handleUpgrade}
            disabled={tier.name.toLowerCase() !== 'pro'} // Only Pro is purchasable
            className={`w-full font-bold py-3 rounded-lg shadow-lg transition-colors ${tier.name.toLowerCase() === 'pro'
                ? 'bg-gradient-to-r from-accent-blue to-accent-green text-white'
                : 'bg-dark-border text-text-secondary cursor-not-allowed'
              }`}>
            {tier.name === 'Pro' ? 'Upgrade to Pro' : 'Select Plan'}
          </button>
        )}
      </div>
    </motion.div>
  );
};

const SubscriptionTiers = ({ currentPlan }) => {
  const tiers = [
    {
      name: 'Free',
      price: '₹0',
      description: 'For individuals and small businesses getting started with GST reconciliation.',
      features: [
        'Unlimited reconciliations',
        'Process up to 1,000 invoices per file',
        'Email support',
        'Standard reconciliation features'
      ],
      highlight: false,
    },
    {
      name: 'Pro',
      price: '₹499 + GST / year',
      description: 'For professionals and businesses requiring unlimited processing and advanced features.',
      features: [
        'Unlimited reconciliations',
        'Process up to 10,000 invoices per file',
        'Priority email & chat support',
        'Save and load column mappings',
        'Advanced mismatch analysis (coming soon)'
      ],
      highlight: true,
    },
  ];

  return (
    <div className="py-20 px-4">
      <div className="text-center max-w-3xl mx-auto mb-12">
        <h2 className="text-4xl md:text-5xl font-bold mb-4">Unlock Your Full Potential</h2>
        <p className="text-lg text-text-secondary">
          Choose the plan that’s right for you. Go Pro for unlimited access and advanced features.
        </p>
      </div>
      <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-8">
        {tiers.map((tier) => (
          <TierCard key={tier.name} tier={tier} currentPlan={currentPlan} />
        ))}
      </div>
    </div>
  );
};

export default SubscriptionTiers;
