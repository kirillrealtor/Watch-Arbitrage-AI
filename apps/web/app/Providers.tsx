'use client';

import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { theme } from '../theme/create-chronoarb-theme';
import { ReactNode } from 'react';

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider theme={theme}>
      {/* CssBaseline kicks off an elegant, consistent, and simple baseline to build upon. */}
      {/* It's used here because MUI is now our primary component system. Tailwind preflight will coexist gracefully through proper layer ordering. */}
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
