export interface NavigationItem {
  label: string;
  to: string;
  description: string;
  group: "Overview" | "Planning" | "Execution" | "Resolution" | "Administration";
}
