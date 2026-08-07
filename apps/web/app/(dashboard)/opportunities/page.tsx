import { PageHeader } from '../../../components/shell/PageHeader';
import { Box, Typography } from '@mui/material';

export default function OpportunitiesPage() {
  return (
    <Box>
      <PageHeader 
        title="Opportunities" 
        description="View and evaluate current watch arbitrage opportunities."
      />
      <Box className="px-4 sm:px-6 lg:px-8">
        <Typography variant="body1" color="text.secondary">
          Opportunity feed implementation begins in a later frontend phase.
        </Typography>
      </Box>
    </Box>
  );
}
