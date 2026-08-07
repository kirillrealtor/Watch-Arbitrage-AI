import { PageHeader } from '../../../../components/shell/PageHeader';
import { Box, Typography } from '@mui/material';

export default function SettingsOrganizationPage() {
  return (
    <Box>
      <PageHeader 
        title="Organization Settings" 
        description="Manage your dealership preferences and team access."
      />
      <Box className="px-4 sm:px-6 lg:px-8">
        <Typography variant="body1" color="text.secondary">
          Settings implementation begins in a later frontend phase.
        </Typography>
      </Box>
    </Box>
  );
}
