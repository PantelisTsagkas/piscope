import {
  BarChart3,
  FlaskConical,
  Grid3x3,
  History,
  Info,
  LayoutDashboard,
  Search,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/explorer", label: "Digit Explorer", icon: Grid3x3 },
  { href: "/search", label: "Sequence Search", icon: Search },
  { href: "/frequency", label: "Frequency Analysis", icon: BarChart3 },
  { href: "/lab", label: "Statistical Lab", icon: FlaskConical },
  { href: "/experiments", label: "Experiments", icon: History },
  { href: "/about", label: "About", icon: Info },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
