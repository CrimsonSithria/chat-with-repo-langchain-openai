import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography } from '@mui/material';
import ForceGraph2D from 'react-force-graph-2d';

interface Node {
  id: string;
  name: string;
  type: 'function' | 'class' | 'module';
  is_core?: boolean;
}

interface Link {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

interface SimpleGraphProps {
  indexId?: string;
}

const SimpleGraph: React.FC<SimpleGraphProps> = ({ indexId }) => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [error, setError] = useState<string | null>(null);
  const graphRef = useRef();

  useEffect(() => {
    if (!indexId) return;

    const fetchData = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/code-structure/${indexId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch code structure');
        }
        const data = await response.json();
        setGraphData(data);
      } catch (err) {
        console.error('Error fetching code structure:', err);
        setError('Failed to load code structure');
      }
    };

    fetchData();
  }, [indexId]);

  const getNodeColor = (node: Node) => {
    if (!node.is_core && node.type !== 'module') return '#e0e0e0';
    switch (node.type) {
      case 'function': return node.is_core ? '#1976d2' : '#90caf9';
      case 'class': return node.is_core ? '#c2185b' : '#f48fb1';
      case 'module': return node.is_core ? '#2e7d32' : '#81c784';
      default: return '#e0e0e0';
    }
  };

  return (
    <Box sx={{ height: '100%', width: '100%', position: 'relative' }}>
      {error && (
        <Box sx={{ p: 2, color: 'error.main' }}>
          <Typography>{error}</Typography>
        </Box>
      )}
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeLabel="name"
        nodeColor={getNodeColor}
        linkDirectionalParticles={2}
        nodeRelSize={6}
        backgroundColor="#ffffff"
      />
    </Box>
  );
};

export default SimpleGraph; 