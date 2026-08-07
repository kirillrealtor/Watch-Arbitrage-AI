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
        <Box 
          sx={{ 
            p: 3, 
            display: 'flex', 
            flexDirection: 'column',
            justifyContent: 'center',
            minHeight: 72,
            borderBottom: '1px solid',
            borderColor: 'divider',
            mb: 2,
            bgcolor: 'background.paper',
          }}
        >
          <Typography 
            variant="overline" 
            color="text.primary" 
            sx={{ 
              fontWeight: 700, 
              letterSpacing: '0.1em',
              lineHeight: 1.2
            }}
          >
            CHRONOARB
          </Typography>
          <Typography 
            variant="caption" 
            color="text.secondary"
            sx={{ 
              fontWeight: 500,
              letterSpacing: '0.02em',
              mt: 0.5
            }}
          >
            Dealer Intelligence
          </Typography>
        </Box>
        <Box sx={{ overflow: 'auto', flex: 1, bgcolor: 'background.paper' }}>
          <NavLinks />
        </Box>
      </nav>
    </Drawer>
  );
}
