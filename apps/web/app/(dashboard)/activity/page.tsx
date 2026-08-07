import { PageHeader } from '../../../components/shell/PageHeader';
import { Box, Typography } from '@mui/material';

export default function ActivityPage() {
  return (
    <Box>
      <PageHeader 
        title="Activity" 
        description="Review your past actions and system events."
      />
      <Box className="px-4 sm:px-6 lg:px-8">
        <Typography variant="body1" color="text.secondary">
          Activity log implementation begins in a later frontend phase.
        </Typography>
      </Box>
    </Box>
  );
}
