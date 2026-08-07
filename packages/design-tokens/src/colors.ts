export const colors = {
  slate: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },
  blue: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb', // Primary
    700: '#1d4ed8', // Primary hover
    800: '#1e40af', // Primary active
    900: '#1e3a8a',
    950: '#172554',
  },
  emerald: {
    50: '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981',
    600: '#059669', // Success
    700: '#047857', // Opp positive
    800: '#065f46',
    900: '#064e3b',
    950: '#022c22',
  },
  amber: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b', // Warning
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
    950: '#451a03',
  },
  rose: {
    50: '#fff1f2',
    100: '#ffe4e6',
    200: '#fecdd3',
    300: '#fda4af',
    400: '#fb7185',
    500: '#f43f5e',
    600: '#e11d48', // Danger/Error
    700: '#be123c', // Opp risk
    800: '#9f1239',
    900: '#881337',
    950: '#4c0519',
  },
  white: '#ffffff',
  black: '#000000',
  transparent: 'transparent',
};

// Semantic roles (light theme mappings)
export const semanticColors = {
  background: {
    default: colors.slate[50],
    paper: colors.white,
  },
  text: {
    primary: colors.slate[900],
    secondary: colors.slate[600], // Increased contrast (slate-500 failed on slate-50)
  },
  divider: colors.slate[200],
  primary: {
    main: colors.blue[600],
    light: colors.blue[500],
    dark: colors.blue[700],
    contrastText: colors.white,
  },
  success: {
    main: colors.emerald[700], // Increased contrast for white text
    light: colors.emerald[600],
    dark: colors.emerald[800],
    contrastText: colors.white,
  },
  warning: {
    main: colors.amber[500],
    light: colors.amber[400],
    dark: colors.amber[600],
    contrastText: colors.slate[900],
  },
  error: {
    main: colors.rose[700], // Increased contrast for white text
    light: colors.rose[600],
    dark: colors.rose[800],
    contrastText: colors.white,
  },
  info: {
    main: colors.blue[500],
    light: colors.blue[400],
    dark: colors.blue[600],
    contrastText: colors.white,
  },
  // Custom ChronoArb roles
  chronoarb: {
    opportunityPositive: colors.emerald[700],
    opportunityRisk: colors.rose[700],
  },
  action: {
    active: colors.slate[500],
    hover: colors.slate[100],
    selected: colors.blue[50],
    disabled: colors.slate[300],
    disabledBackground: colors.slate[100],
    focus: colors.blue[500],
  }
};
