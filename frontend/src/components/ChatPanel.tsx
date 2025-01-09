import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemText,
  Alert,
  AppBar,
  Toolbar,
  Typography,
  Button,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SyncIcon from '@mui/icons-material/Sync';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import typescript from 'react-syntax-highlighter/dist/esm/languages/hljs/typescript';
import { vs2015 } from 'react-syntax-highlighter/dist/esm/styles/hljs';

// Register languages
SyntaxHighlighter.registerLanguage('typescript', typescript);

interface CodeChunk {
  content: string;
  file: string;
  start_line: number;
  end_line: number;
}

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  chunks?: CodeChunk[];
}

interface Progress {
  current_file: string;
  total_files: number;
  processed_files: number;
  status: string;
}

interface ChatPanelProps {
  indexId?: string;
  onSwitchIndex?: () => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ indexId = 'default', onSwitchIndex }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const progressWs = useRef<WebSocket | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Initialize WebSocket connection
    const connectWebSocket = () => {
      if (!indexId) return;

      const wsUrl = `ws://localhost:8000/ws/chat/${indexId}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket Connected');
        setWsConnected(true);
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket Closed:', event.code, event.reason);
        setWsConnected(false);
        // Attempt to reconnect after 2 seconds
        setTimeout(connectWebSocket, 2000);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket Error:', error);
      };

      ws.current.onmessage = (event) => {
        const response = JSON.parse(event.data);
        
        // Handle heartbeat
        if (response.type === 'ping') {
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'pong' }));
          }
          return;
        }

        // Handle error messages
        if (response.type === 'error') {
          console.error('Server error:', response.message);
          return;
        }

        const botMessage: Message = {
          id: Date.now(),
          text: response.message,
          sender: 'bot',
          timestamp: new Date(),
          chunks: response.chunks
        };
        setMessages(prev => [...prev, botMessage]);
      };
    };

    connectWebSocket();

    // Cleanup function
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [indexId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Initialize progress WebSocket
    const connectProgressWs = () => {
      progressWs.current = new WebSocket('ws://localhost:8000/ws/progress');
      
      progressWs.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'ping') {
          progressWs.current?.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        if (data.type === 'progress') {
          setProgress(data);
        }
      };

      progressWs.current.onclose = (event) => {
        console.log('Progress WebSocket Disconnected', event.code, event.reason);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectProgressWs, 3000);
      };

      progressWs.current.onerror = (error) => {
        console.error('Progress WebSocket Error:', error);
      };
    };

    connectProgressWs();

    return () => {
      if (progressWs.current) {
        progressWs.current.close();
      }
    };
  }, []);

  const handleSend = () => {
    if (input.trim() && ws.current && ws.current.readyState === WebSocket.OPEN) {
      const newMessage: Message = {
        id: Date.now(),
        text: input,
        sender: 'user',
        timestamp: new Date(),
      };
      setMessages([...messages, newMessage]);
      ws.current.send(JSON.stringify({ message: input }));
      setInput('');
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const renderCodeChunk = (chunk: CodeChunk) => (
    <Box sx={{ mt: 1 }}>
      <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
        {chunk.file} (lines {chunk.start_line}-{chunk.end_line})
      </Typography>
      <Paper sx={{ maxHeight: 300, overflow: 'auto' }}>
        <SyntaxHighlighter
          language="typescript"
          style={vs2015}
          customStyle={{ margin: 0, borderRadius: 0, background: 'transparent' }}
        >
          {chunk.content}
        </SyntaxHighlighter>
      </Paper>
    </Box>
  );

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      bgcolor: 'background.paper' 
    }}>
      <AppBar position="static" color="default" elevation={0}>
        <Toolbar variant="dense">
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
            Index: {indexId}
          </Typography>
          <Button
            size="small"
            startIcon={<SyncIcon />}
            onClick={onSwitchIndex}
          >
            Switch Index
          </Button>
        </Toolbar>
      </AppBar>

      {!wsConnected && (
        <Alert severity="warning" sx={{ m: 1 }}>
          Connecting to server...
        </Alert>
      )}

      {progress && progress.status !== 'idle' && progress.status !== 'completed' && (
        <Alert severity="info" sx={{ m: 1 }}>
          {progress.status === 'starting' ? (
            'Starting indexing...'
          ) : (
            <>
              Indexing: {progress.current_file}
              <br />
              Progress: {progress.processed_files} / {progress.total_files} files
            </>
          )}
        </Alert>
      )}
      
      {/* Messages List */}
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        p: 2,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <List>
          {messages.map((message) => (
            <ListItem
              key={message.id}
              sx={{
                justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                mb: 1,
                flexDirection: 'column',
                alignItems: message.sender === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  width: message.chunks ? '100%' : 'auto',
                  bgcolor: message.sender === 'user' ? 'primary.dark' : 'background.paper',
                }}
              >
                <ListItemText
                  primary={message.text}
                  secondary={message.timestamp.toLocaleTimeString()}
                  sx={{
                    '& .MuiListItemText-primary': {
                      color: message.sender === 'user' ? 'white' : 'text.primary',
                    },
                    '& .MuiListItemText-secondary': {
                      color: message.sender === 'user' ? 'rgba(255,255,255,0.7)' : 'text.secondary',
                    },
                  }}
                />
                {message.chunks && message.chunks.map((chunk, idx) => (
                  renderCodeChunk(chunk)
                ))}
              </Paper>
            </ListItem>
          ))}
        </List>
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box sx={{ p: 2, bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            variant="outlined"
            size="small"
            disabled={!wsConnected}
          />
          <IconButton 
            color="primary" 
            onClick={handleSend} 
            disabled={!wsConnected || !input.trim()}
            sx={{ ml: 1 }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatPanel; 