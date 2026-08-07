"use client";

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { AppBar, Toolbar, IconButton, Typography, Drawer, Box } from '@mui/material';
import MenuOutlinedIcon from '@mui/icons-material/MenuOutlined';
import { NavLinks } from './NavLinks';
import { navigationConfig, isRouteActive } from '../../config/navigation';

export function MobileNavigation() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };



  // Determine current section title
  const currentNav = navigationConfig.find(item => isRouteActive(pathname, item));
  const title = currentNav ? currentNav.label : 'ChronoArb';

  return (
    <>
      <AppBar 
        position="static" 
        color="inherit" 
        elevation={1}
        sx={{ 
          display: { xs: 'block', lg: 'none' },
          borderBottom: '1px solid',
          borderColor: 'divider',
          boxShadow: 'none',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="Open navigation"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            <MenuOutlinedIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
            {title}
          </Typography>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', lg: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 256 },
        }}
      >
        <nav aria-label="Mobile navigation" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Box sx={{ p: 3, display: 'flex', alignItems: 'center', height: 64 }}>
            <Typography variant="h6" color="text.primary" sx={{ fontWeight: 'bold' }}>
              ChronoArb
            </Typography>
          </Box>
          <Box sx={{ overflow: 'auto', flex: 1 }}>
            <NavLinks onItemClick={() => setMobileOpen(false)} />
          </Box>
        </nav>
      </Drawer>
    </>
  );
}
