import React, { useEffect, useRef, useState } from 'react';
import { ForceGraph2D } from 'react-force-graph';
import { Box, Typography, IconButton, Tooltip } from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong';
import * as d3 from 'd3-force';

interface Node {
  id: string;
  name: string;
  type: 'function' | 'class' | 'module';
  color?: string;
  size?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface Link {
  source: Node;
  target: Node;
  type: 'calls' | 'imports' | 'inherits';
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
  const graphRef = useRef<any>();

  useEffect(() => {
    if (!indexId) return;

    const fetchCodeStructure = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/code-structure/${indexId}`);
        if (response.ok) {
          const data = await response.json();
          // Transform string IDs to objects for D3
          const nodesById = Object.fromEntries(data.nodes.map((node: Node) => [node.id, node]));
          const transformedLinks = data.links.map((link: any) => ({
            ...link,
            source: nodesById[link.source],
            target: nodesById[link.target]
          }));
          setGraphData({
            nodes: data.nodes,
            links: transformedLinks
          });
        }
      } catch (error) {
        console.error('Failed to fetch code structure:', error);
      }
    };

    fetchCodeStructure();
  }, [indexId]);

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
    switch (node.type) {
      case 'function':
        return '#90caf9';
      case 'class':
        return '#f48fb1';
      case 'module':
        return '#81c784';
      default:
        return '#e0e0e0';
    }
  };

  const getLinkColor = (link: Link) => {
    switch (link.type) {
      case 'calls':
        return '#64b5f6';
      case 'imports':
        return '#81c784';
      case 'inherits':
        return '#f48fb1';
      default:
        return '#e0e0e0';
    }
  };

  const graphProps = {
    graphData,
    nodeColor: getNodeColor,
    linkColor: getLinkColor,
    nodeLabel: "name",
    linkDirectionalParticles: 2,
    linkDirectionalParticleSpeed: 0.005,
    d3VelocityDecay: 0.4,
    nodeRelSize: 8,
    backgroundColor: '#ffffff',
    d3Force: {
      link: d3.forceLink()
        .id((d: any) => d.id)
        .distance((link: any) => {
          switch (link.type) {
            case 'inherits':
              return 250;
            case 'imports':
              return 200;
            default:
              return 150;
          }
        })
        .strength((link: any) => {
          switch (link.type) {
            case 'inherits':
              return 0.3;
            case 'imports':
              return 0.2;
            default:
              return 0.1;
          }
        }),
      charge: d3.forceManyBody()
        .strength(node => (node as any).type === 'module' ? -400 : -200)
        .distanceMax(500),
      center: d3.forceCenter(),
      collide: d3.forceCollide()
        .radius(50)
        .strength(1)
    },
    nodeCanvasObject: (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name;
      const fontSize = Math.max(16, 24/globalScale);
      ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
      const textWidth = ctx.measureText(label).width;
      const nodeSize = node.type === 'module' ? 8 : 6;
      const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 1.2);

      // Draw node circle with a border
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI);
      ctx.fillStyle = getNodeColor(node as Node);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw label background with shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
      ctx.shadowBlur = 5;
      ctx.shadowOffsetX = 2;
      ctx.shadowOffsetY = 2;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.fillRect(
        node.x - bckgDimensions[0] / 2,
        node.y - bckgDimensions[1] / 2,
        bckgDimensions[0],
        bckgDimensions[1]
      );

      // Reset shadow for text
      ctx.shadowColor = 'transparent';
      
      // Draw label text
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#000';
      ctx.fillText(label, node.x, node.y);

      // Draw type indicator
      ctx.font = `${fontSize * 0.7}px Inter, system-ui, sans-serif`;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillText(node.type, node.x, node.y + fontSize);
    },
    linkWidth: (link: any) => {
      switch (link.type) {
        case 'inherits':
          return 3;
        case 'imports':
          return 2;
        default:
          return 1;
      }
    },
    linkDirectionalArrowLength: 8,
    linkDirectionalArrowRelPos: 0.8,
    linkCurvature: (link: any) => {
      return link.type === 'inherits' ? 0.2 : 0;
    },
    cooldownTicks: 50,
    onEngineStop: () => {
      if (graphRef.current) {
        graphRef.current.zoomToFit(400, 100);
      }
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

      <ForceGraph2D
        ref={graphRef}
        {...graphProps}
      />
    </Box>
  );
};

export default CodeVisualizer; 