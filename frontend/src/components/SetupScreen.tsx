import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Button,
  Paper,
  Divider,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  LinearProgress,
} from '@mui/material';

interface Index {
  id: string;
  name: string;
}

interface Progress {
  current_file: string;
  total_files: number;
  processed_files: number;
  status: string;
}

interface SetupScreenProps {
  onIndexSelect: (indexId: string) => void;
  onNewIndex: () => void;
}

const SetupScreen: React.FC<SetupScreenProps> = ({ onIndexSelect, onNewIndex }) => {
  const [indices, setIndices] = useState<Index[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [repoPath, setRepoPath] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);

  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/indices');
        if (!response.ok) {
          throw new Error('Failed to fetch indices');
        }
        const data = await response.json();
        setIndices(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching indices:', err);
        setError('Failed to load indices. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchIndices();
  }, []);

  useEffect(() => {
    // Connect to progress WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/progress');
    
    ws.onopen = () => {
      console.log('Progress WebSocket Connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
        return;
      }
      if (data.type === 'progress') {
        setProgress({
          current_file: data.current_file,
          total_files: data.total_files,
          processed_files: data.processed_files,
          status: data.status
        });
        
        // If indexing is complete, refresh the indices list
        if (data.status === 'complete') {
          setTimeout(() => {
            setProgress(null);
            setIsCreating(false);
            fetchIndices();
          }, 1000);
        }
      }
    };

    ws.onclose = () => {
      console.log('Progress WebSocket closed');
    };

    return () => {
      ws.close();
    };
  }, []);

  const fetchIndices = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/indices');
      if (!response.ok) {
        throw new Error('Failed to fetch indices');
      }
      const data = await response.json();
      setIndices(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching indices:', err);
      setError('Failed to load indices. Please try again.');
    }
  };

  const handleCreateIndex = async (path: string) => {
    setIsCreating(true);
    setError(null);
    try {
      // Clean up the path
      const cleanPath = path.trim();
      if (!cleanPath) {
        throw new Error('Please enter a valid repository path');
      }

      const response = await fetch('http://localhost:8000/api/indices/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_path: cleanPath }),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to create index');
      }
      
      if (data.success) {
        setDialogOpen(false);
        onIndexSelect(data.id);
      } else {
        throw new Error(data.error || 'Failed to create index');
      }
    } catch (err) {
      console.error('Error creating index:', err);
      setError(err instanceof Error ? err.message : 'Failed to create index. Please try again.');
      setIsCreating(false);
    }
  };

  const handleOpenDialog = () => {
    setDialogOpen(true);
    setError(null);
    setRepoPath('');
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setError(null);
  };

  return (
    <Box sx={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      p: 3,
    }}>
      <Paper elevation={3} sx={{ maxWidth: 600, width: '100%', p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Welcome to Chat with Repository
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Select an existing index or create a new one to begin.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {progress && progress.status !== 'idle' && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Indexing in progress...
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              {progress.current_file}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={(progress.processed_files / progress.total_files) * 100} 
              sx={{ mb: 1 }}
            />
            <Typography variant="caption" color="text.secondary">
              {progress.processed_files} / {progress.total_files} files processed
            </Typography>
          </Box>
        )}

        <Typography variant="subtitle1" sx={{ mt: 3, mb: 1 }}>
          Available Indices:
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
            {indices.length === 0 ? (
              <ListItem>
                <ListItemText 
                  primary="No indices found"
                  secondary="Create a new index to get started"
                />
              </ListItem>
            ) : (
              indices.map((index) => (
                <ListItem key={index.id} disablePadding>
                  <ListItemButton onClick={() => onIndexSelect(index.id)}>
                    <ListItemText 
                      primary={`${index.name}`}
                    />
                  </ListItemButton>
                </ListItem>
              ))
            )}
          </List>
        )}

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            onClick={handleOpenDialog}
            disabled={loading || isCreating}
          >
            Create New Index
          </Button>
          <Button
            variant="contained"
            onClick={() => handleCreateIndex('.')}
            disabled={loading || isCreating}
          >
            {isCreating ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              'Analyze Root Folder'
            )}
          </Button>
        </Box>
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>Create New Index</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter the absolute path to the repository you want to analyze.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Repository Path"
            fullWidth
            variant="outlined"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            disabled={isCreating}
            placeholder="/absolute/path/to/repository"
            helperText="Enter the full path to your repository (e.g., /Users/username/Projects/repo-name)"
          />
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            onClick={() => handleCreateIndex(repoPath)}
            variant="contained"
            disabled={isCreating}
          >
            {isCreating ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              'Create Index'
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SetupScreen; 