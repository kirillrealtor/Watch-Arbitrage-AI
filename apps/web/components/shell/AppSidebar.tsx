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
          position: 'static',
          borderRight: '1px solid',
          borderColor: 'divider',
          height: '100%',
        },
      }}
    >
      <nav aria-label="Sidebar navigation" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box
          sx={{
            px: 3,
            py: 2.5,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            minHeight: 64,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography
            variant="overline"
            sx={{
              fontWeight: 700,
              letterSpacing: '0.12em',
              lineHeight: 1.2,
              color: 'text.primary',
              fontSize: '0.75rem',
            }}
          >
            CHRONOARB
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 500,
              letterSpacing: '0.02em',
              mt: 0.25,
              color: 'text.secondary',
              fontSize: '0.6875rem',
            }}
          >
            Dealer Intelligence
          </Typography>
        </Box>
        <Box sx={{ overflow: 'auto', flex: 1 }}>
          <NavLinks />
        </Box>
      </nav>
    </Drawer>
  );
}
