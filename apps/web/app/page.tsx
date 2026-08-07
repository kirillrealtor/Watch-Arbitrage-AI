"use client";

import React from 'react';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import SearchOutlinedIcon from '@mui/icons-material/SearchOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';

export default function DesignSystemPreview() {
  return (
    <div className="min-h-screen bg-slate-50 p-8 sm:p-12 lg:p-24 flex justify-center">
      <div className="w-full max-w-[1024px] space-y-12">
        <header className="border-b border-slate-200 pb-6 mb-8">
          <Typography variant="overline" color="text.secondary">
            ChronoArb
          </Typography>
          <Typography variant="h1" color="text.primary">
            Design System Foundation
          </Typography>
          <Typography variant="body1" color="text.secondary" className="mt-2">
            Development Preview
          </Typography>
        </header>

        <section className="space-y-6">
          <Typography variant="h2" color="text.primary">
            Typography & Content
          </Typography>
          <Paper variant="outlined" className="p-6">
            <div className="space-y-4">
              <Typography variant="h3" color="text.primary">
                Section Heading (H3)
              </Typography>
              <Typography variant="body1" color="text.primary">
                This is standard body text for dense analytical displays. The layout rhythm is based on a strict 4px grid.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                This is secondary body text used for metadata and descriptions that need less emphasis.
              </Typography>
            </div>
          </Paper>
        </section>

        <section className="space-y-6">
          <Typography variant="h2" color="text.primary">
            Financial Presentation
          </Typography>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <Paper variant="outlined" className="p-6 flex flex-col gap-2">
              <Typography variant="caption" color="text.secondary" className="uppercase tracking-wider">
                Expected Profit
              </Typography>
              <Typography variant="h3" color="opportunityPositive.main" className="tabular-nums">
                +$12,500 USD
              </Typography>
            </Paper>

            <Paper variant="outlined" className="p-6 flex flex-col gap-2">
              <Typography variant="caption" color="text.secondary" className="uppercase tracking-wider">
                Acquisition
              </Typography>
              <Typography variant="h3" color="text.primary" className="tabular-nums">
                $24,000 USD
              </Typography>
            </Paper>

            <Paper variant="outlined" className="p-6 flex flex-col gap-2">
              <Typography variant="caption" color="text.secondary" className="uppercase tracking-wider">
                Expected Resale
              </Typography>
              <Typography variant="h3" color="text.primary" className="tabular-nums">
                $36,500 USD
              </Typography>
            </Paper>
          </div>
        </section>

        <section className="space-y-6">
          <Typography variant="h2" color="text.primary">
            Interactive Controls & States
          </Typography>
          <Paper variant="outlined" className="p-6 space-y-8">
            <div className="flex flex-wrap items-center gap-4">
              <Button variant="contained" color="primary" startIcon={<SearchOutlinedIcon />}>
                Search Inventory
              </Button>
              <Button variant="outlined" color="primary" startIcon={<SettingsOutlinedIcon />}>
                Settings
              </Button>
              <Button variant="text" color="primary" disabled>
                Disabled Action
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <Chip 
                label="Published" 
                color="primary" 
                variant="outlined" 
                size="small" 
              />
              <Chip 
                label="Purchased" 
                color="success" 
                variant="filled" 
                size="small" 
                icon={<CheckCircleOutlinedIcon fontSize="small" />} 
              />
              <Chip 
                label="Pending" 
                color="warning" 
                variant="filled" 
                size="small" 
                icon={<WarningAmberOutlinedIcon fontSize="small" />} 
              />
              <Chip 
                label="Viewed" 
                color="default" 
                variant="outlined" 
                size="small" 
              />
            </div>
          </Paper>
        </section>
      </div>
    </div>
  );
}
