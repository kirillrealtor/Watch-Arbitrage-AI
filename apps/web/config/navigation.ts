import RadarOutlinedIcon from '@mui/icons-material/RadarOutlined';
import WatchOutlinedIcon from '@mui/icons-material/WatchOutlined';
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';

export interface NavigationItem {
  label: string;
  href: string;
  icon: React.ElementType;
  /**
   * Defines how the active route is matched against the current pathname.
   * 'prefix' matches if the pathname starts with the href (useful for sections like /settings/*)
   * 'exact' matches only if the pathname is exactly the href
   */
  matchRule: 'exact' | 'prefix';
}

export const navigationConfig: NavigationItem[] = [
  {
    label: 'Opportunities',
    href: '/opportunities',
    icon: RadarOutlinedIcon,
    matchRule: 'prefix',
  },
  {
    label: 'Watches',
    href: '/watches',
    icon: WatchOutlinedIcon,
    matchRule: 'prefix',
  },
  {
    label: 'Alerts',
    href: '/alerts',
    icon: NotificationsActiveOutlinedIcon,
    matchRule: 'prefix',
  },
  {
    label: 'Activity',
    href: '/activity',
    icon: HistoryOutlinedIcon,
    matchRule: 'prefix',
  },
  {
    label: 'Settings',
    href: '/settings/organization',
    icon: SettingsOutlinedIcon,
    // We match /settings globally to cover /settings/organization, /settings/billing, etc.
    matchRule: 'prefix',
  },
];

export function isRouteActive(pathname: string, item: NavigationItem): boolean {
  if (item.matchRule === 'exact') {
    return pathname === item.href;
  }
  
  if (item.matchRule === 'prefix') {
    // Determine the base section, e.g. for /settings/organization it is /settings
    const sectionHref = item.href.split('/').slice(0, 2).join('/');
    // Check if the current pathname starts with the base section and it's either exactly the section
    // or it is followed by a slash. This prevents /settings matching /settings-other (though unlikely).
    return pathname === sectionHref || pathname.startsWith(`${sectionHref}/`);
  }
  
  return false;
}
