import React, { useEffect, useRef, useState } from 'react';
import { Box, TextField, IconButton, Typography } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChatPanelProps {
  indexId?: string;
  onSwitchIndex?: () => void;
}

interface Message {
  type: 'chat' | 'log';
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: {
    tokenUsage?: {
      prompt: number;
      completion: number;
      total: number;
      reasoning?: number;
    };
    chunksInfo?: {
      count: number;
      total_tokens: number;
      chunks: Array<{
        file: string;
        start_line: number;
        end_line: number;
        tokens: number;
        distance: number;
      }>;
    };
    timestamp?: string;
    level?: 'info' | 'error' | 'status';
  };
}

interface Progress {
  current_file: string;
  total_files: number;
  processed_files: number;
  status: string;
}

interface CodeChunk {
  content: string;
  language: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ indexId, onSwitchIndex }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const progressWs = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!indexId) return;

    const connectWebSocket = () => {
      // Connect to chat WebSocket
      if (ws.current?.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected');
        return;
      }

      console.log('Connecting to chat WebSocket...');
      ws.current = new WebSocket(`ws://localhost:8000/ws/chat/${indexId}`);
      
      ws.current.onopen = () => {
        console.log('WebSocket Connected');
        setError(null);
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received message:', data);
        
        if (data.type === 'ping') {
          ws.current?.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        
        if (data.type === 'chat') {
          const newMessage: Message = {
            type: 'chat',
            role: data.role,
            content: data.content,
            metadata: {
              tokenUsage: data.token_usage,
              chunksInfo: data.chunks_info,
              timestamp: new Date().toLocaleTimeString()
            }
          };
          console.log('Processing chat message:', {
            role: data.role,
            tokenUsage: data.token_usage,
            chunksInfo: data.chunks_info
          });
          setMessages(prev => [...prev, newMessage]);
          scrollToBottom();
        } else if (data.type === 'log' || data.type === 'error') {
          const logMessage: Message = {
            type: 'log',
            role: 'system',
            content: data.content,
            metadata: {
              timestamp: new Date().toLocaleTimeString(),
              level: data.type === 'error' ? 'error' : 'info'
            }
          };
          console.log(`Processing ${data.type} message:`, data.content);
          setMessages(prev => [...prev, logMessage]);
          scrollToBottom();
          
          if (data.type === 'error') {
            setError(data.content);
          }
        } else if (data.type === 'status') {
          const statusMessage: Message = {
            type: 'log',
            role: 'system',
            content: `Status: ${data.content}`,
            metadata: {
              timestamp: new Date().toLocaleTimeString(),
              level: 'status'
            }
          };
          console.log('Processing status message:', data.content);
          setMessages(prev => [...prev, statusMessage]);
          scrollToBottom();
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error. Attempting to reconnect...');
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setError('Connection lost. Attempting to reconnect...');
        // Attempt to reconnect after 2 seconds
        setTimeout(connectWebSocket, 2000);
      };
    };

    const connectProgressWebSocket = () => {
      // Connect to progress WebSocket
      if (progressWs.current?.readyState === WebSocket.OPEN) {
        console.log('Progress WebSocket already connected');
        return;
      }

      console.log('Connecting to progress WebSocket...');
      progressWs.current = new WebSocket('ws://localhost:8000/ws/progress');
      
      progressWs.current.onopen = () => {
        console.log('Progress WebSocket Connected');
      };

      progressWs.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received progress:', data);
        
        if (data.type === 'ping') {
          progressWs.current?.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        if (data.type === 'progress') {
          setProgress({
            current_file: data.current_file,
            total_files: data.total_files,
            processed_files: data.processed_files,
            status: data.status
          });
        }
      };

      progressWs.current.onerror = (error) => {
        console.error('Progress WebSocket error:', error);
      };

      progressWs.current.onclose = (event) => {
        console.log('Progress WebSocket closed:', event.code, event.reason);
        // Attempt to reconnect after 2 seconds
        setTimeout(connectProgressWebSocket, 2000);
      };
    };

    // Initial connections
    connectWebSocket();
    connectProgressWebSocket();

    // Cleanup on unmount
    return () => {
      console.log('Cleaning up WebSocket connections...');
      if (ws.current) {
        ws.current.close();
      }
      if (progressWs.current) {
        progressWs.current.close();
      }
    };
  }, [indexId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws.current) return;

    const userMessage: Message = {
      type: 'chat',
      role: 'user',
      content: input
    };

    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInput('');
    setError(null);

    try {
      await ws.current.send(JSON.stringify({
        type: 'chat',
        content: input
      }));
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  const renderMessage = (message: Message) => {
    // Split content into text and code blocks
    const parts = message.content.split(/(```[a-z]*\n[\s\S]*?\n```)/g);
    
    return (
      <Box
        sx={{
          mb: 2,
          alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
          maxWidth: message.role === 'system' ? '100%' : '80%'
        }}
      >
        <Box
          sx={{
            bgcolor: message.role === 'user' ? 'primary.main' : 
                    message.role === 'system' ? 'grey.200' : 'grey.100',
            color: message.role === 'user' ? 'white' : 'text.primary',
            p: 2,
            borderRadius: 2,
            fontFamily: message.role === 'system' ? 'monospace' : 'inherit',
            fontSize: message.role === 'system' ? '0.85rem' : 'inherit',
            '& pre': {
              margin: 0,
              padding: 0
            }
          }}
        >
          {message.role === 'system' && (
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
              System Log - {message.metadata?.timestamp}
            </Typography>
          )}
          {parts.map((part, i) => {
            if (part.startsWith('```')) {
              // Extract language and code
              const match = part.match(/```([a-z]*)\n([\s\S]*?)\n```/);
              if (match) {
                const [, language, code] = match;
                return (
                  <Box key={i} sx={{ my: 1 }}>
                    <SyntaxHighlighter
                      language={language || 'text'}
                      style={vscDarkPlus}
                      customStyle={{
                        margin: 0,
                        borderRadius: '4px',
                        fontSize: '0.9rem'
                      }}
                    >
                      {code.trim()}
                    </SyntaxHighlighter>
                  </Box>
                );
              }
            }
            // Regular text
            return (
              <Typography
                key={i}
                variant="body1"
                component="div"
                sx={{
                  whiteSpace: 'pre-wrap',
                  '& p': { margin: '0.5em 0' },
                  '& p:first-of-type': { marginTop: 0 },
                  '& p:last-of-type': { marginBottom: 0 }
                }}
              >
                {part}
              </Typography>
            );
          })}
          {(message.metadata?.tokenUsage || message.metadata?.chunksInfo) && message.role !== 'system' && (
            <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(0,0,0,0.1)', fontSize: '0.8rem', color: 'text.secondary' }}>
              {message.metadata.chunksInfo && (
                <Typography variant="caption" display="block" sx={{ mb: 0.5 }}>
                  Chunks: {message.metadata.chunksInfo.count} (Total tokens: {message.metadata.chunksInfo.total_tokens})
                  {message.metadata.chunksInfo.chunks.map((chunk, idx) => (
                    <Box key={idx} component="span" display="block" sx={{ ml: 1, fontSize: '0.75rem' }}>
                      • {chunk.file.split('/').pop()} (Lines {chunk.start_line}-{chunk.end_line}, {chunk.tokens} tokens, dist: {chunk.distance.toFixed(3)})
                    </Box>
                  ))}
                </Typography>
              )}
              {message.metadata.tokenUsage && (
                <Typography variant="caption" display="block">
                  Token Usage:
                  {message.metadata.tokenUsage.prompt && ` Prompt: ${message.metadata.tokenUsage.prompt}`}
                  {message.metadata.tokenUsage.completion && ` Completion: ${message.metadata.tokenUsage.completion}`}
                  {message.metadata.tokenUsage.total && ` Total: ${message.metadata.tokenUsage.total}`}
                  {message.metadata.tokenUsage.reasoning && ` Reasoning: ${message.metadata.tokenUsage.reasoning}`}
                </Typography>
              )}
              {message.metadata.timestamp && (
                <Typography variant="caption" display="block">
                  Time: {message.metadata.timestamp}
                </Typography>
              )}
            </Box>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      bgcolor: 'background.paper'
    }}>
      <Box sx={{
        flex: 1,
        overflow: 'auto',
        p: 2,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {messages.map((message, index) => (
          <React.Fragment key={index}>
            {renderMessage(message)}
          </React.Fragment>
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {error && (
        <Typography color="error" sx={{ px: 2, py: 1 }}>
          {error}
        </Typography>
      )}

      {progress && progress.status !== 'idle' && (
        <Box sx={{ px: 2, py: 1, bgcolor: 'grey.100' }}>
          <Typography variant="body2">
            Processing: {progress.current_file}
            <br />
            Progress: {progress.processed_files}/{progress.total_files} files
          </Typography>
        </Box>
      )}

      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}
      >
        <Box sx={{ display: 'flex', gap: 1 }}>
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
          />
          <IconButton
            color="primary"
            onClick={handleSubmit}
            disabled={!input.trim()}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatPanel; 