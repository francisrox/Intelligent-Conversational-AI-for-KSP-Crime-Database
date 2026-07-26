import React, { useEffect, useRef } from "react";
import cytoscape from "cytoscape";

const TYPE_COLORS = {
  Accused: "#4F9DDE",
  Crime: "#E0A458",
  Vehicle: "#3FB68B",
  Victim: "#8B98A5",
};

function labelFor(data) {
  return data.name || data.fir_no || data.plate_no || String(data.id);
}

export default function GraphCanvas({ nodes, edges, height = 380 }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }
    if (!nodes || nodes.length === 0) return;

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele) => TYPE_COLORS[ele.data("type")] || "#566373",
            label: (ele) => labelFor(ele.data()),
            color: "#E6EDF3",
            "font-size": 9,
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 28,
            height: 28,
            "border-width": 2,
            "border-color": "#0B0F14",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#324153",
            "target-arrow-color": "#324153",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.7,
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 7,
            color: "#566373",
            "text-rotation": "autorotate",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 24, nodeRepulsion: 8000 },
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [nodes, edges]);

  if (!nodes || nodes.length === 0) {
    return null;
  }

  return <div ref={containerRef} className="graph-canvas" style={{ height }} />;
}
