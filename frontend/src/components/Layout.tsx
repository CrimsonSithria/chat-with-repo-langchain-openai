import React, { useState } from 'react';
import { Box, Paper, Grid } from '@mui/material';
import CodeVisualizer from './CodeVisualizer';
import ChatPanel from './ChatPanel';
import SetupScreen from './SetupScreen';

type AppState = 'setup' | 'chat';

const Layout: React.FC = () => {
  const [appState, setAppState] = useState<AppState>('setup');
  const [currentIndex, setCurrentIndex] = useState<string | null>(null);

  const handleIndexSelect = (indexId: string) => {
    setCurrentIndex(indexId);
    setAppState('chat');
  };

  const handleNewIndex = () => {
    // TODO: Implement new index creation flow
    console.log('Creating new index...');
  };

  const handleSwitchIndex = () => {
    setAppState('setup');
  };

  if (appState === 'setup') {
    return <SetupScreen onIndexSelect={handleIndexSelect} onNewIndex={handleNewIndex} />;
  }

  return (
    <Box sx={{ flexGrow: 1, height: '100vh', overflow: 'hidden' }}>
      <Grid container sx={{ height: '100%' }}>
        {/* Code Visualization Panel */}
        <Grid item xs={7} sx={{ height: '100%', position: 'relative' }}>
          <Paper 
            elevation={3} 
            sx={{ 
              height: '100%', 
              borderRadius: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0
            }}
          >
            <CodeVisualizer indexId={currentIndex || undefined} />
          </Paper>
        </Grid>

        {/* Chat Panel */}
        <Grid item xs={5} sx={{ height: '100%', position: 'relative' }}>
          <Paper 
            elevation={3} 
            sx={{ 
              height: '100%', 
              borderRadius: 0,
              borderLeft: '1px solid rgba(255, 255, 255, 0.12)',
              display: 'flex',
              flexDirection: 'column',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0
            }}
          >
            <ChatPanel 
              indexId={currentIndex || undefined}
              onSwitchIndex={handleSwitchIndex}
            />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Layout; 