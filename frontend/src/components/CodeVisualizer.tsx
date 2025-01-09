import React, { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Box, Typography, IconButton, Tooltip } from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong';
import * as d3 from 'd3';

interface Node {
  id: string;
  name: string;
  type: 'function' | 'class' | 'module';
  is_core?: boolean;
  color?: string;
  size?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface Link {
  source: string | Node;
  target: string | Node;
  type: 'calls' | 'imports' | 'inherits' | 'belongs_to';
  value?: number;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

interface CodeVisualizerProps {
  indexId?: string;
}

const CodeVisualizer: React.FC<CodeVisualizerProps> = ({ indexId }) => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [error, setError] = useState<string | null>(null);
  const graphRef = useRef<any>();

  useEffect(() => {
    if (!indexId) return;

    const fetchCodeStructure = async () => {
      try {
        console.log('Fetching code structure for index:', indexId);
        const response = await fetch(`http://localhost:8000/api/code-structure/${indexId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch code structure: ${response.statusText}`);
        }
        const data = await response.json();
        console.log('Received graph data:', data);
        
        if (!data.nodes || !data.links) {
          console.error('Invalid graph data structure:', data);
          throw new Error('Invalid graph data structure');
        }

        if (data.nodes.length === 0) {
          console.warn('No nodes found in the code structure');
          setError('No code structure found. The repository might be empty or contain no analyzable code.');
          return;
        }
        
        // Transform string IDs to objects for D3
        const nodesById = Object.fromEntries(data.nodes.map((node: Node) => [node.id, node]));
        const transformedLinks = data.links.map((link: any) => ({
          ...link,
          source: nodesById[link.source],
          target: nodesById[link.target]
        }));

        // Filter out non-core nodes and their links
        const coreNodes = data.nodes.filter((node: Node) => node.is_core || node.type === 'module');
        const coreNodeIds = new Set(coreNodes.map((node: Node) => node.id));
        const coreLinks = transformedLinks.filter((link: Link) => 
          typeof link.source === 'object' && 
          typeof link.target === 'object' && 
          coreNodeIds.has(link.source.id) && 
          coreNodeIds.has(link.target.id)
        );

        console.log('Processed graph data:', {
          nodes: coreNodes.length,
          links: coreLinks.length
        });

        // Only update if we have valid data
        if (coreNodes.length > 0) {
          setGraphData({
            nodes: coreNodes,
            links: coreLinks
          });
          
          // Center the graph after data is loaded
          setTimeout(() => {
            if (graphRef.current) {
              console.log('Centering graph');
              graphRef.current.zoomToFit(400);
            }
          }, 500);
        } else {
          setError('No nodes found in the code structure');
        }
      } catch (error) {
        console.error('Failed to fetch code structure:', error);
        setError(error instanceof Error ? error.message : 'Failed to load code structure');
      }
    };

    // Initial fetch
    fetchCodeStructure();

    // Refresh data periodically
    const intervalId = setInterval(fetchCodeStructure, 30000);

    return () => {
      clearInterval(intervalId);
    };
  }, [indexId]);

  // Prevent graph from disappearing on window resize
  useEffect(() => {
    const handleResize = () => {
      if (graphRef.current) {
        graphRef.current.centerAt(0, 0, 1);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleZoomIn = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom * 1.5, 400);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom / 1.5, 400);
    }
  };

  const handleCenter = () => {
    if (graphRef.current) {
      graphRef.current.centerAt(0, 0, 1000);
      graphRef.current.zoom(1, 1000);
    }
  };

  const getNodeColor = (node: Node) => {
    if (!node.is_core && node.type !== 'module') {
      return '#e0e0e0';
    }
    switch (node.type) {
      case 'function':
        return node.is_core ? '#1976d2' : '#90caf9';
      case 'class':
        return node.is_core ? '#c2185b' : '#f48fb1';
      case 'module':
        return node.is_core ? '#2e7d32' : '#81c784';
      default:
        return '#e0e0e0';
    }
  };

  const getLinkColor = (link: Link) => {
    switch (link.type) {
      case 'calls':
        return '#1976d2';
      case 'imports':
        return '#2e7d32';
      case 'inherits':
        return '#c2185b';
      case 'belongs_to':
        return '#9e9e9e';
      default:
        return '#e0e0e0';
    }
  };

  return (
    <Box sx={{ 
      height: '100%', 
      position: 'relative',
      bgcolor: 'background.paper',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {error && (
        <Box sx={{ p: 2, color: 'error.main' }}>
          <Typography>{error}</Typography>
        </Box>
      )}

      <Box sx={{ 
        position: 'absolute', 
        top: 16, 
        right: 16, 
        zIndex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        bgcolor: 'background.paper',
        borderRadius: 1,
        p: 0.5,
        boxShadow: 1
      }}>
        <Tooltip title="Zoom In" placement="left">
          <IconButton size="small" onClick={handleZoomIn}>
            <ZoomInIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom Out" placement="left">
          <IconButton size="small" onClick={handleZoomOut}>
            <ZoomOutIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Center Graph" placement="left">
          <IconButton size="small" onClick={handleCenter}>
            <CenterFocusStrongIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ 
        position: 'absolute', 
        top: 16, 
        left: 16, 
        zIndex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        bgcolor: 'background.paper',
        borderRadius: 1,
        p: 1,
        boxShadow: 1
      }}>
        <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Legend:</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#90caf9' }} />
          <Typography variant="caption">Function</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#f48fb1' }} />
          <Typography variant="caption">Class</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#81c784' }} />
          <Typography variant="caption">Module</Typography>
        </Box>
      </Box>

      <Box sx={{ 
        flexGrow: 1, 
        position: 'relative',
        width: '100%',
        height: '100%',
        '& > div': {
          width: '100% !important',
          height: '100% !important'
        }
      }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeColor={getNodeColor}
          linkColor={getLinkColor}
          nodeLabel="name"
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          nodeRelSize={8}
          backgroundColor="#ffffff"
          onNodeClick={(node) => {
            console.log('Clicked node:', node);
          }}
          cooldownTicks={100}
          cooldownTime={2000}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const label = node.name;
            const fontSize = Math.max(12, 16/globalScale);
            ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
            const textWidth = ctx.measureText(label).width;
            const nodeSize = 
              node.type === 'module' ? 12 :
              node.type === 'class' ? 8 :
              6;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.8);

            // Draw node circle with a border
            ctx.beginPath();
            ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI);
            ctx.fillStyle = getNodeColor(node as Node);
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Draw label background
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            ctx.fillRect(
              node.x - bckgDimensions[0] / 2,
              node.y - bckgDimensions[1] / 2,
              bckgDimensions[0],
              bckgDimensions[1]
            );

            // Draw label text
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#000';
            ctx.fillText(label, node.x, node.y);
          }}
        />
      </Box>
    </Box>
  );
};

export default CodeVisualizer; 