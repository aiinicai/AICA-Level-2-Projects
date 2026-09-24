import {
  Compass,
  Database,
  FileText,
  Home,
  LayoutDashboard,
  Plug,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const NAV: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/dashboards", label: "Dashboards", icon: LayoutDashboard },
  { to: "/data-sources", label: "Data Sources", icon: Database },
  { to: "/explorer", label: "Data Explorer", icon: Compass },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/automations", label: "Automations", icon: Zap },
  { to: "/integrations", label: "Integrations", icon: Plug },
  { to: "/team", label: "Team", icon: Users },
];

export const MOBILE_NAV: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/dashboards", label: "Dashboards", icon: LayoutDashboard },
  { to: "/explorer", label: "Data", icon: Compass },
  { to: "/reports", label: "Reports", icon: FileText },
];
