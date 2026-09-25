import React from 'react'
import CytoscapeComponent from 'react-cytoscapejs'

const nodeColors = {
  USER: '#3b82f6',
  DEVICE: '#6b7280',
  IP: '#a78bfa',
  UNKNOWN: '#4b5563',
}

const suspiciousColor = '#ef4444'

export default function InvestigationGraph({ graph }) {
  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    return (
      <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">INVESTIGATION GRAPH</h3>
        <div className="h-64 flex items-center justify-center text-gray-500 text-sm">
          No graph data available
        </div>
      </div>
    )
  }

  const elements = [
    ...graph.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        suspicious: node.suspicious,
        node_type: node.node_type,
      },
      style: {
        backgroundColor: node.suspicious ? suspiciousColor : (nodeColors[node.node_type] || '#4b5563'),
        label: node.label,
        color: '#fff',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '10px',
        width: node.suspicious ? 50 : 40,
        height: node.suspicious ? 50 : 40,
        'border-width': node.suspicious ? 3 : 1,
        'border-color': node.suspicious ? '#fca5a5' : '#374151',
      },
    })),
    ...graph.edges.map((edge, i) => ({
      data: {
        id: `e${i}`,
        source: edge.source,
        target: edge.target,
        label: edge.relationship,
      },
      style: {
        label: edge.relationship,
        'font-size': '8px',
        color: '#6b7280',
        'text-rotation': 'autorotate',
        'text-margin-y': -8,
        width: 1.5,
        'line-color': '#374151',
        'target-arrow-color': '#374151',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
      },
    })),
  ]

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': '#4b5563',
        label: 'data(label)',
        color: '#fff',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '10px',
      },
    },
    {
      selector: 'edge',
      style: {
        width: 1.5,
        'line-color': '#374151',
        'target-arrow-color': '#374151',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        label: 'data(label)',
        'font-size': '8px',
        color: '#6b7280',
        'text-rotation': 'autorotate',
        'text-margin-y': -8,
      },
    },
  ]

  return (
    <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">INVESTIGATION GRAPH</h3>
      <div className="rounded bg-surface overflow-hidden">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          style={{ width: '100%', height: '350px' }}
          layout={{
            name: 'cose',
            animate: false,
            nodeRepulsion: 8000,
            idealEdgeLength: 100,
          }}
          minZoom={0.5}
          maxZoom={2}
        />
      </div>
      <div className="flex gap-4 mt-2 text-xs text-gray-500">
        <span><span className="inline-block w-3 h-3 rounded bg-fraud-blue mr-1" /> USER</span>
        <span><span className="inline-block w-3 h-3 rounded bg-gray-500 mr-1" /> DEVICE</span>
        <span><span className="inline-block w-3 h-3 rounded bg-purple-400 mr-1" /> IP</span>
        <span><span className="inline-block w-3 h-3 rounded bg-fraud-red mr-1" /> SUSPICIOUS</span>
      </div>
    </div>
  )
}
