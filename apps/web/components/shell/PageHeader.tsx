import { Box, Typography } from '@mui/material';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <Box 
      className="px-6 sm:px-8 lg:px-10 py-8 mb-8" 
      sx={{ 
        bgcolor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
        boxShadow: '0 1px 2px rgba(0,0,0,0.02)', // ultra-subtle depth
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 3 }}>
        <Box sx={{ maxWidth: '800px' }}>
          <Typography 
            variant="h4" 
            component="h1" 
            color="text.primary" 
            sx={{ 
              fontWeight: 700,
              letterSpacing: '-0.02em',
              mb: description ? 1 : 0
            }}
          >
            {title}
          </Typography>
          {description && (
            <Typography 
              variant="body1" 
              color="text.secondary" 
              sx={{ 
                lineHeight: 1.6,
                maxWidth: '600px'
              }}
            >
              {description}
            </Typography>
          )}
        </Box>
        {actions && (
          <Box sx={{ ml: 2, display: 'flex', gap: 1 }}>
            {actions}
          </Box>
        )}
      </Box>
    </Box>
  );
}
