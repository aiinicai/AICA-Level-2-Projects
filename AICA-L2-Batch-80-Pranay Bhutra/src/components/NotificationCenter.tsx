import React, { useState, useEffect } from 'react';
import {
  Bell,
  Send,
  MessageSquare,
  Mail,
  Smartphone,
  CheckCheck,
  Clock,
  CheckCircle2,
  ExternalLink,
  ArrowRight,
  Package,
  Truck
} from 'lucide-react';
import { NotificationLog, ThemeStyle, UserProfile } from '../types';
import { ParcelStorageService } from '../services/storage';
import { THEMES } from '../utils/theme';

interface NotificationCenterProps {
  currentUser?: UserProfile;
  currentTheme?: ThemeStyle;
  onNavigateToShipment?: (referenceNumber: string, trackingNumber: string, type: 'inward' | 'outward') => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  currentUser,
  currentTheme = 'navy',
  onNavigateToShipment,
}) => {
  const [notifications, setNotifications] = useState<NotificationLog[]>([]);
  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  useEffect(() => {
    setNotifications(ParcelStorageService.getNotifications(currentUser?.organizationId));
    const handleUpdate = (e: any) => setNotifications(e.detail || []);
    window.addEventListener('notifications_updated', handleUpdate);
    return () => window.removeEventListener('notifications_updated', handleUpdate);
  }, [currentUser?.organizationId]);

  const getChannelIcon = (channel: NotificationLog['channel']) => {
    switch (channel) {
      case 'WhatsApp':
        return { icon: MessageSquare, color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20' };
      case 'Email':
        return { icon: Mail, color: `${themeConfig.textAccent} ${themeConfig.badgeBg} border` };
      default:
        return { icon: Bell, color: 'text-purple-500 bg-purple-500/10 border-purple-500/20' };
    }
  };

  const handleNotificationClick = (item: NotificationLog) => {
    // Mark as read in storage
    ParcelStorageService.markNotificationAsRead(item.id);

    if (onNavigateToShipment) {
      const isOutward =
        item.referenceNumber?.startsWith('OUT') ||
        item.type.toLowerCase().includes('outward') ||
        item.type.toLowerCase().includes('dispatched');
      const targetType: 'inward' | 'outward' = isOutward ? 'outward' : 'inward';
      onNavigateToShipment(item.referenceNumber, item.trackingNumber, targetType);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${themeConfig.cardBg} p-4 rounded-xl border ${themeConfig.cardBorder} backdrop-blur-sm shadow-sm transition-colors duration-300`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${themeConfig.badgeBg} border ${themeConfig.textAccent}`}>
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h2 className={`text-base font-bold ${themeConfig.textPrimary} flex items-center gap-2`}>
              Automated Stakeholder Notifications & Activity Alerts
              <span className={`text-xs px-2 py-0.5 rounded-full ${themeConfig.subCardBg} ${themeConfig.textSecondary} font-mono border ${themeConfig.cardBorder}`}>
                {notifications.length} Logs
              </span>
            </h2>
            <p className={`text-xs ${themeConfig.textMuted}`}>
              Click any notification to immediately jump to and view the relevant courier activity and consignment record.
            </p>
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className={`rounded-xl border ${themeConfig.cardBorder} ${themeConfig.cardBg} overflow-hidden divide-y ${themeConfig.cardBorder} shadow-lg transition-colors duration-300`}>
        {notifications.length === 0 ? (
          <div className={`p-8 text-center ${themeConfig.textMuted} text-xs`}>
            No automated notification logs recorded yet.
          </div>
        ) : (
          notifications.map((item) => {
            const channelInfo = getChannelIcon(item.channel);
            const Icon = channelInfo.icon;
            const isUnread = item.status === 'Sent' || item.status === 'Delivered';
            const isOutward =
              item.referenceNumber?.startsWith('OUT') ||
              item.type.toLowerCase().includes('outward') ||
              item.type.toLowerCase().includes('dispatched');

            return (
              <div
                key={item.id}
                onClick={() => handleNotificationClick(item)}
                className={`p-4 ${themeConfig.cardHover} cursor-pointer transition-all flex flex-col sm:flex-row sm:items-start justify-between gap-3 text-xs group ${
                  isUnread ? `${themeConfig.subCardBg} border-l-4 ${themeConfig.borderAccent}` : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2.5 rounded-xl border ${channelInfo.color} shrink-0 mt-0.5 group-hover:scale-105 transition-transform`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-semibold ${themeConfig.textPrimary}`}>
                        {item.type}
                      </span>
                      <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${themeConfig.subCardBg} ${themeConfig.textAccent} border ${themeConfig.cardBorder} font-bold`}>
                        {item.referenceNumber || `AWB #${item.trackingNumber}`}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded ${themeConfig.subCardBg} ${themeConfig.textMuted}`}>
                        Via {item.channel}
                      </span>
                      {isUnread && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30 uppercase tracking-wider">
                          New
                        </span>
                      )}
                    </div>

                    <p className={`${themeConfig.textSecondary} text-xs mt-1.5 leading-relaxed ${themeConfig.subCardBg} p-2.5 rounded-lg border ${themeConfig.cardBorder} transition-colors`}>
                      {item.message}
                    </p>

                    <div className={`flex items-center gap-3 mt-2 text-[11px] ${themeConfig.textMuted}`}>
                      <span>Recipient: <b className={themeConfig.textPrimary}>{item.recipient}</b></span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className={`w-3 h-3 ${themeConfig.textMuted}`} />
                        {item.timestamp}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:self-center shrink-0">
                  <span className={`text-xs font-semibold ${themeConfig.textAccent} group-hover:translate-x-1 transition-transform flex items-center gap-1`}>
                    <span>View {isOutward ? 'Dispatch' : 'Inward'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
