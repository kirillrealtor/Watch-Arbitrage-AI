"use client";

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import { navigationConfig, isRouteActive } from '../../config/navigation';

interface NavLinksProps {
  onItemClick?: () => void;
}

export function NavLinks({ onItemClick }: NavLinksProps) {
  const pathname = usePathname();

  return (
    <List component="nav" sx={{ px: 2, py: 1 }}>
      {navigationConfig.map((item) => {
        // Handle hydration safety implicitly; active will evaluate to something stable 
        // because pathname is available in Next.js Client Components during SSR.
        const active = isRouteActive(pathname, item);
        const Icon = item.icon;

        return (
          <ListItem key={item.href} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              component={Link}
              href={item.href}
              selected={active}
              onClick={onItemClick}
              aria-current={active ? (pathname === item.href ? 'page' : 'location') : undefined}
              sx={{
                borderRadius: 1,
                // Add specific visual styling for selected state as requested:
                // text/icon emphasis + subtle background
                '&.Mui-selected': {
                  bgcolor: 'action.selected',
                  '&:hover': {
                    bgcolor: 'action.selected', // keep it stable on hover
                  },
                }
              }}
            >
              <ListItemIcon 
                sx={{ 
                  minWidth: 40,
                  color: active ? 'primary.main' : 'text.secondary' 
                }}
              >
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText 
                primary={
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: active ? 600 : 500,
                      color: active ? 'primary.main' : 'text.primary',
                    }}
                  >
                    {item.label}
                  </Typography>
                }
              />
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
  );
}
