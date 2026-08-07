import { PageHeader } from '../../../components/shell/PageHeader';
import { Box, Typography } from '@mui/material';

export default function AlertsPage() {
  return (
    <Box>
      <PageHeader 
        title="Alerts" 
        description="Manage your matching rules and notifications."
      />
      <Box className="px-4 sm:px-6 lg:px-8">
        <Typography variant="body1" color="text.secondary">
          Alert configuration implementation begins in a later frontend phase.
        </Typography>
      </Box>
    </Box>
  );
}
