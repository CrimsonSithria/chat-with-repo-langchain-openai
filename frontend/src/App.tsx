import React, { useState, useEffect } from 'react';
import { Box, Button, Dialog, DialogTitle, DialogContent, List, ListItem, ListItemText, TextField, Typography } from '@mui/material';
import ChatPanel from './components/ChatPanel';
import CodeVisualizer from './components/CodeVisualizer';

interface Index {
  id: string;
  name: string;
}

const App: React.FC = () => {
  const [indices, setIndices] = useState<Index[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(true);
  const [repoPath, setRepoPath] = useState('.');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIndices();
  }, []);

  const fetchIndices = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/indices');
      if (!response.ok) {
        throw new Error('Failed to fetch indices');
      }
      const data = await response.json();
      setIndices(data);
    } catch (error) {
      console.error('Error fetching indices:', error);
      setError('Failed to fetch available indices');
    }
  };

  const handleCreateIndex = async () => {
    try {
      setError(null);
      const response = await fetch('http://localhost:8000/api/indices/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_path: repoPath }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create index');
      }

      const data = await response.json();
      if (data.success) {
        await fetchIndices();
        setSelectedIndex(data.id);
        setIsDialogOpen(false);
      } else {
        throw new Error(data.error || 'Failed to create index');
      }
    } catch (error) {
      console.error('Error creating index:', error);
      setError(error instanceof Error ? error.message : 'Failed to create index');
    }
  };

  const handleSelectIndex = (indexId: string) => {
    setSelectedIndex(indexId);
    setIsDialogOpen(false);
  };

  const handleSwitchIndex = () => {
    setIsDialogOpen(true);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Dialog open={isDialogOpen} maxWidth="sm" fullWidth>
        <DialogTitle>Welcome to Chat with Repository</DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Select an existing index or create a new one to begin.
          </Typography>

          {error && (
            <Typography color="error" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )}

          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Available Indices:
          </Typography>

          <List sx={{ mb: 2 }}>
            {indices.map((index) => (
              <ListItem
                key={index.id}
                button
                onClick={() => handleSelectIndex(index.id)}
              >
                <ListItemText primary={index.name} />
              </ListItem>
            ))}
          </List>

          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Create New Index:
          </Typography>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
            <TextField
              fullWidth
              label="Repository Path"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              size="small"
              helperText="Enter '.' to analyze the current directory"
            />
            <Button
              variant="contained"
              onClick={handleCreateIndex}
              sx={{ minWidth: 120 }}
            >
              Create Index
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {selectedIndex && (
        <Box sx={{ display: 'flex', height: '100%' }}>
          <Box sx={{ width: '50%', height: '100%', borderRight: 1, borderColor: 'divider' }}>
            <ChatPanel indexId={selectedIndex} onSwitchIndex={handleSwitchIndex} />
          </Box>
          <Box sx={{ width: '50%', height: '100%' }}>
            <CodeVisualizer indexId={selectedIndex} />
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default App;
