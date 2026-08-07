import { PageHeader } from '../../../components/shell/PageHeader';
import { Box, Typography, Paper } from '@mui/material';
import ConstructionOutlinedIcon from '@mui/icons-material/ConstructionOutlined';

export default function AlertsPage() {
  return (
    <Box>
      <PageHeader 
        title="Alerts" 
        description="Manage your matching rules and notifications."
      />
      <Box className="px-6 sm:px-8 lg:px-10">
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 4, 
            maxWidth: 'sm', 
            display: 'flex', 
            gap: 2, 
            alignItems: 'flex-start',
            bgcolor: 'background.paper',
            borderColor: 'divider',
          }}
        >
          <ConstructionOutlinedIcon color="disabled" />
          <Box>
            <Typography variant="subtitle2" color="text.primary" sx={{ mb: 0.5, fontWeight: 600 }}>
              Development placeholder
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
              Alert configuration implementation begins in a later frontend phase.
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
