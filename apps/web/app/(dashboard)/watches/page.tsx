import { PageHeader } from '../../../components/shell/PageHeader';
import { Box, Typography } from '@mui/material';

export default function WatchesPage() {
  return (
    <Box>
      <PageHeader 
        title="Watches" 
        description="Search and explore the normalized watch catalog."
      />
      <Box className="px-4 sm:px-6 lg:px-8">
        <Typography variant="body1" color="text.secondary">
          Watch catalog implementation begins in a later frontend phase.
        </Typography>
      </Box>
    </Box>
  );
}
