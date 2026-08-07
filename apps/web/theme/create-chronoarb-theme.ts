import { createTheme } from '@mui/material/styles';
import {
  darkSemanticColors,
  typography,
  spacing,
  radii,
  breakpoints,
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
  },
  palette: {
    mode: 'dark',
    background: darkSemanticColors.background,
    text: darkSemanticColors.text,
    divider: darkSemanticColors.divider,
    primary: darkSemanticColors.primary,
    success: darkSemanticColors.success,
    warning: darkSemanticColors.warning,
    error: darkSemanticColors.error,
    info: darkSemanticColors.info,
    opportunityPositive: {
      main: darkSemanticColors.chronoarb.opportunityPositive,
    },
    opportunityRisk: {
      main: darkSemanticColors.chronoarb.opportunityRisk,
    },
    action: {
      active: darkSemanticColors.action.active,
      hover: darkSemanticColors.action.hover,
      selected: darkSemanticColors.action.selected,
      disabled: darkSemanticColors.action.disabled,
      disabledBackground: darkSemanticColors.action.disabledBackground,
      focus: darkSemanticColors.action.focus,
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
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  spacing: spacing,
  shape: {
    borderRadius: radii.md,
  },
  breakpoints: breakpoints,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: darkSemanticColors.background.default,
          color: darkSemanticColors.text.primary,
        },
      },
    },
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
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: darkSemanticColors.background.sidebar,
          borderRight: `1px solid ${darkSemanticColors.divider}`,
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: darkSemanticColors.action.hover,
          },
          '&.Mui-selected': {
            backgroundColor: darkSemanticColors.action.selected,
            '&:hover': {
              backgroundColor: darkSemanticColors.action.selected,
            },
          },
        },
      },
    },
    MuiListItemIcon: {
      styleOverrides: {
        root: {
          color: 'inherit',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: darkSemanticColors.background.sidebar,
          borderBottom: `1px solid ${darkSemanticColors.divider}`,
          boxShadow: 'none',
        },
      },
    },
    MuiToolbar: {
      styleOverrides: {
        root: {
          minHeight: 64,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: darkSemanticColors.divider,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
  },
});
