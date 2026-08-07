import { Drawer, Box, Typography } from '@mui/material';
import { NavLinks } from './NavLinks';

export function AppSidebar() {
  return (
    <Drawer
      variant="permanent"
      sx={{
        display: { xs: 'none', lg: 'block' },
        width: 256,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 256,
          boxSizing: 'border-box',
          position: 'static', // Make paper participate in flex instead of fixed position
          borderRight: '1px solid',
          borderColor: 'divider',
          height: '100%',
        },
      }}
    >
      <nav aria-label="Sidebar navigation" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{ p: 3, display: 'flex', alignItems: 'center', height: 64 }}>
          <Typography variant="h6" color="text.primary" sx={{ fontWeight: 'bold' }}>
            ChronoArb
          </Typography>
        </Box>
        <Box sx={{ overflow: 'auto', flex: 1 }}>
          <NavLinks />
        </Box>
      </nav>
    </Drawer>
  );
}
