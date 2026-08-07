"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Box,
} from '@mui/material';
import { navigationConfig, isRouteActive } from '../../config/navigation';

interface NavLinksProps {
  onItemClick?: () => void;
}

export function NavLinks({ onItemClick }: NavLinksProps) {
  const pathname = usePathname();

  return (
    <List component="nav" sx={{ px: 2, py: 2 }}>
      {navigationConfig.map((item) => {
        const active = isRouteActive(pathname, item);
        const Icon = item.icon;
        const isSettings = item.label === 'Settings';

        return (
          <React.Fragment key={item.href}>
            {isSettings && (
              <Box sx={{ mt: 2, mb: 2, px: 2 }}>
                <Divider />
              </Box>
            )}
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                component={Link}
                href={item.href}
                selected={active}
                onClick={onItemClick}
                aria-current={active ? (pathname === item.href ? 'page' : 'location') : undefined}
                sx={{
                  borderRadius: 1,
                  py: 0.75,
                  px: 1.5,
                  position: 'relative',
                  color: 'text.secondary',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    bgcolor: 'action.hover',
                    color: 'text.primary',
                  },
                  '&.Mui-selected': {
                    bgcolor: 'transparent',
                    color: 'primary.main',
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      left: -8, // pull outside the padding
                      top: '15%',
                      bottom: '15%',
                      width: 3,
                      bgcolor: 'primary.main',
                      borderRadius: '0 4px 4px 0',
                    }
                  }
                }}
              >
                <ListItemIcon 
                  sx={{ 
                    minWidth: 36,
                    color: 'inherit',
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
                        color: 'inherit',
                        letterSpacing: '0.01em',
                      }}
                    >
                      {item.label}
                    </Typography>
                  }
                />
              </ListItemButton>
            </ListItem>
          </React.Fragment>
        );
      })}
    </List>
  );
}
