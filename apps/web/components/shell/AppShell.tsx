import { AppSidebar } from './AppSidebar';
import { MobileNavigation } from './MobileNavigation';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col lg:flex-row h-[100dvh] overflow-hidden">
      {/* Skip to main content link */}
      <a 
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:p-4 focus:font-bold"
        style={{ 
          backgroundColor: 'var(--mui-palette-background-paper)', 
          color: 'var(--mui-palette-primary-main)' 
        }}
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <AppSidebar />

      {/* Main Column */}
      <div 
        className="flex flex-col flex-1 min-w-0 min-h-0"
        style={{ backgroundColor: 'var(--mui-palette-background-default)' }}
      >
        {/* Mobile Navigation (includes AppBar) */}
        <MobileNavigation />

        {/* Main Content Area */}
        <main 
          id="main-content" 
          className="flex-1 min-h-0 overflow-y-auto" 
          tabIndex={-1} 
          style={{ outline: 'none' }} // avoid focus ring when clicking into main area, but keep it focusable for skip link
        >
          {children}
        </main>
      </div>
    </div>
  );
}
