import { createTheme } from '@mui/material/styles';
import { 
  semanticColors, 
  typography, 
  spacing, 
  radii,
  breakpoints 
} from '@chronoarb/design-tokens';

declare module '@mui/material/styles' {
  interface Palette {
    opportunityPositive: Palette['primary'];
    opportunityRisk: Palette['primary'];
  }
  interface PaletteOptions {
    opportunityPositive?: PaletteOptions['primary'];
    opportunityRisk?: PaletteOptions['primary'];
  }
}

declare module '@mui/material/styles' {
  interface BreakpointOverrides {
    xs: true;
    sm: true;
    md: true;
    lg: true;
    xl: true;
    '2xl': true;
  }
}

export const theme = createTheme({
  cssVariables: {
    colorSchemeSelector: 'class',
    disableCssColorScheme: true, // We are explicitly enforcing light theme only for MVP
  },
  palette: {
    mode: 'light',
    background: semanticColors.background,
    text: semanticColors.text,
    divider: semanticColors.divider,
    primary: semanticColors.primary,
    success: semanticColors.success,
    warning: semanticColors.warning,
    error: semanticColors.error,
    info: semanticColors.info,
    opportunityPositive: {
      main: semanticColors.chronoarb.opportunityPositive,
    },
    opportunityRisk: {
      main: semanticColors.chronoarb.opportunityRisk,
    },
    action: {
      active: semanticColors.action.active,
      hover: semanticColors.action.hover,
      selected: semanticColors.action.selected,
      disabled: semanticColors.action.disabled,
      disabledBackground: semanticColors.action.disabledBackground,
      focus: semanticColors.action.focus,
    },
  },
  typography: {
    fontFamily: typography.fontFamily,
    h1: typography.h1,
    h2: typography.h2,
    h3: typography.h3,
    body1: typography.body1,
    body2: typography.body2,
    caption: typography.caption,
    overline: typography.overline,
    button: {
      textTransform: 'none', // Prevent default uppercase for buttons
      fontWeight: 500,
    }
  },
  spacing: spacing,
  shape: {
    borderRadius: radii.md,
  },
  breakpoints: breakpoints,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none', // Remove elevation overlay
        },
      },
    },
  },
});
