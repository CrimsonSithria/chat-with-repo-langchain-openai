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
    <Box sx={{ 
      height: '100vh', 
      width: '100vw',
      overflow: 'hidden',
      display: 'flex'
    }}>
      <Grid container sx={{ flexGrow: 1 }}>
        {/* Code Visualization Panel */}
        <Grid item xs={7} sx={{ height: '100vh', position: 'relative' }}>
          <Paper 
            elevation={3} 
            sx={{ 
              height: '100%',
              width: '100%',
              borderRadius: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}
          >
            <CodeVisualizer indexId={currentIndex || undefined} />
          </Paper>
        </Grid>

        {/* Chat Panel */}
        <Grid item xs={5} sx={{ height: '100vh' }}>
          <Paper 
            elevation={3} 
            sx={{ 
              height: '100%',
              borderRadius: 0,
              borderLeft: '1px solid rgba(255, 255, 255, 0.12)',
              display: 'flex',
              flexDirection: 'column'
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