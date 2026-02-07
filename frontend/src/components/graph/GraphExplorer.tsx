"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Network } from "lucide-react";

// Dynamic import to avoid SSR issues with canvas
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="animate-pulse text-gray-400">Loading graph...</div>
    </div>
  ),
});

interface GraphNode {
  id: string;
  name: string;
  type: "entity" | "account" | "transaction" | "sanctioned";
  riskScore?: number;
}

interface GraphLink {
  source: string;
  target: string;
  type?: string;
}

interface GraphExplorerProps {
  nodes: GraphNode[];
  links: GraphLink[];
  highlightPath?: string[];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ForceGraphRef = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ForceGraphNodeType = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ForceGraphLinkType = any;

const nodeColors = {
  entity: "#3b82f6", // blue
  account: "#10b981", // green
  transaction: "#8b5cf6", // purple
  sanctioned: "#ef4444", // red
};

export function GraphExplorer({ nodes, links, highlightPath = [] }: GraphExplorerProps) {
  const graphRef = useRef<ForceGraphRef>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Handle responsive sizing
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({
          width: clientWidth || 800,
          height: clientHeight || 600,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    
    // Also observe container size changes
    const resizeObserver = new ResizeObserver(updateDimensions);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener("resize", updateDimensions);
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force("charge").strength(-300);
      graphRef.current.d3Force("link").distance(100);
    }
  }, []);

  const nodeCanvasObject = useCallback(
    (node: ForceGraphNodeType, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const fontSize = 12 / globalScale;
      const isHighlighted = highlightPath.includes(node.id);
      const isSanctioned = node.type === "sanctioned";

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, isHighlighted ? 8 : 6, 0, 2 * Math.PI);
      ctx.fillStyle = nodeColors[node.type as keyof typeof nodeColors] || "#6b7280";
      ctx.fill();

      // Highlight ring
      if (isHighlighted) {
        ctx.beginPath();
        ctx.arc(node.x ?? 0, node.y ?? 0, 12, 0, 2 * Math.PI);
        ctx.strokeStyle = "#fbbf24";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Sanctioned warning
      if (isSanctioned) {
        ctx.beginPath();
        ctx.arc(node.x ?? 0, node.y ?? 0, 10, 0, 2 * Math.PI);
        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Label with background for better visibility
      ctx.font = `bold ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      
      // Measure text for background
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const textHeight = fontSize;
      const padding = 3 / globalScale;
      
      // Draw text background (semi-transparent white/dark)
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
      ctx.fillRect(
        (node.x ?? 0) - textWidth / 2 - padding,
        (node.y ?? 0) + 15 - textHeight / 2 - padding,
        textWidth + padding * 2,
        textHeight + padding * 2
      );
      
      // Draw text border for more contrast
      ctx.strokeStyle = "rgba(0, 0, 0, 0.1)";
      ctx.lineWidth = 1 / globalScale;
      ctx.strokeRect(
        (node.x ?? 0) - textWidth / 2 - padding,
        (node.y ?? 0) + 15 - textHeight / 2 - padding,
        textWidth + padding * 2,
        textHeight + padding * 2
      );
      
      // Draw text with strong contrast
      ctx.fillStyle = "#111827"; // Very dark gray for maximum readability
      ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + 15);
    },
    [highlightPath]
  );

  const linkColor = useCallback(
    (link: ForceGraphLinkType) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;

      if (highlightPath.includes(sourceId) && highlightPath.includes(targetId)) {
        return "#fbbf24"; // Yellow for highlighted path
      }
      return "#d1d5db"; // Gray default
    },
    [highlightPath]
  );

  const linkWidth = useCallback(
    (link: ForceGraphLinkType) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;

      if (highlightPath.includes(sourceId) && highlightPath.includes(targetId)) {
        return 3;
      }
      return 1;
    },
    [highlightPath]
  );

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <Network className="w-12 h-12 mb-4 opacity-50" />
        <p>No graph data available</p>
        <p className="text-sm mt-1">Run an investigation to populate the graph</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full relative bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
      <div className="absolute top-4 left-4 z-10 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
          <Network className="w-4 h-4" />
          Entity Graph
        </h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">Entity</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-600 dark:text-gray-400">Account</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-gray-600 dark:text-gray-400">Transaction</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-600 dark:text-gray-400">Sanctioned</span>
          </div>
        </div>
      </div>

      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        nodeCanvasObject={nodeCanvasObject}
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.8}
        backgroundColor="transparent"
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  );
}
