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
} from '@mui/material';

interface Index {
  id: string;
  name: string;
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

  const handleCreateIndex = async (path: string) => {
    setIsCreating(true);
    try {
      const response = await fetch('http://localhost:8000/api/indices/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_path: path }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create index');
      }
      
      const data = await response.json();
      if (data.success) {
        setDialogOpen(false);
        onIndexSelect(data.id);
      } else {
        throw new Error(data.error || 'Failed to create index');
      }
    } catch (err) {
      console.error('Error creating index:', err);
      setError('Failed to create index. Please try again.');
    } finally {
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
                      secondary={`Index ID: ${index.id}`}
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
            Analyze Root Folder
          </Button>
        </Box>
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCloseDialog}>
        <DialogTitle>Create New Index</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter the path to the repository you want to analyze.
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
            placeholder="e.g., /path/to/repository"
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
            disabled={!repoPath.trim() || isCreating}
          >
            {isCreating ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SetupScreen; 