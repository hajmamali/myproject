/**
 * Knowledge Graph Center Page
 * Graph Builder and Explorer
 */

import { useState } from 'react';
import { apiClient } from '../api/client';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

interface GraphResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
  path?: GraphNode[];
}

export default function KnowledgeGraphCenter() {
  const [searchQuery, setSearchQuery] = useState('');
  const [graphData, setGraphData] = useState<GraphResult | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandDepth, setExpandDepth] = useState(1);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.post<GraphResult>('/api/v1/graph/query', {
        query: searchQuery,
        limit: 50,
      });
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در جستجوی گراف دانش');
    } finally {
      setLoading(false);
    }
  };

  const handleExpandNode = async (nodeId: string) => {
    setLoading(true);
    try {
      const data = await apiClient.post<GraphResult>('/api/v1/graph/expand', {
        node_id: nodeId,
        depth: expandDepth,
      });

      // Merge new nodes and edges
      setGraphData(prev => ({
        nodes: [...(prev?.nodes || []), ...data.nodes],
        edges: [...(prev?.edges || []), ...data.edges],
        path: prev?.path,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در بسط گره گراف');
    } finally {
      setLoading(false);
    }
  };

  const getNodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'legal_case': return 'bg-blue-500';
      case 'law': return 'bg-green-500';
      case 'regulation': return 'bg-purple-500';
      case 'precedent': return 'bg-orange-500';
      case 'concept': return 'bg-pink-500';
      default: return 'bg-slate-500';
    }
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Knowledge Graph Center</h1>
          <p className="text-slate-400">کاوش و ساخت گراف دانش حقوقی</p>
        </div>

        {/* Search Bar */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="جستجوی گره، رابطه، یا مسیر..."
              className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white placeholder-slate-400"
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              {loading ? 'در حال جستجو...' : 'جستجو'}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400 mb-6">
            <p className="font-medium">خطا</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        {graphData && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Graph Visualization */}
            <div className="lg:col-span-2 bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">گراف</h2>
                <div className="flex items-center gap-2">
                  <label className="text-slate-400 text-sm">عمق گسترش:</label>
                  <select
                    value={expandDepth}
                    onChange={(e) => setExpandDepth(Number(e.target.value))}
                    className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-white text-sm"
                  >
                    <option value={1}>۱</option>
                    <option value={2}>۲</option>
                    <option value={3}>۳</option>
                  </select>
                </div>
              </div>

              {/* Simplified Graph View */}
              <div className="bg-slate-900 rounded-lg p-4 min-h-[400px] relative">
                {graphData.nodes.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <p>گرافی برای نمایش وجود ندارد</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {graphData.nodes.map((node) => (
                      <div
                        key={node.id}
                        onClick={() => setSelectedNode(node)}
                        className={`p-3 rounded-lg cursor-pointer transition-colors ${
                          selectedNode?.id === node.id ? 'bg-primary-600' : 'bg-slate-800 hover:bg-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${getNodeColor(node.type)}`} />
                          <div>
                            <div className="text-white font-medium">{node.label}</div>
                            <div className="text-slate-400 text-xs">{node.type}</div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleExpandNode(node.id);
                            }}
                            className="ml-auto text-slate-400 hover:text-white text-sm"
                          >
                            +
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Path Visualization */}
              {graphData.path && graphData.path.length > 0 && (
                <div className="mt-4 bg-slate-900 rounded-lg p-4">
                  <h3 className="text-white font-medium mb-3">مسیر توضیح‌داده شده</h3>
                  <div className="flex items-center gap-2 overflow-x-auto">
                    {graphData.path.map((node, index) => (
                      <div key={node.id} className="flex items-center">
                        <div className={`px-3 py-2 rounded ${getNodeColor(node.type)} text-white text-sm`}>
                          {node.label}
                        </div>
                        {index < graphData.path!.length - 1 && (
                          <div className="mx-2 text-slate-400">→</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Node Details */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">جزئیات گره</h2>
              
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <div className="text-slate-400 text-sm mb-1">شناسه</div>
                    <div className="text-white font-mono text-sm">{selectedNode.id}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-sm mb-1">نام</div>
                    <div className="text-white">{selectedNode.label}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-sm mb-1">نوع</div>
                    <div className="text-white">{selectedNode.type}</div>
                  </div>
                  
                  {/* Properties */}
                  <div>
                    <div className="text-slate-400 text-sm mb-2">ویژگی‌ها</div>
                    <div className="space-y-2">
                      {Object.entries(selectedNode.properties).map(([key, value]) => (
                        <div key={key} className="bg-slate-900 rounded p-2">
                          <div className="text-slate-400 text-xs">{key}</div>
                          <div className="text-white text-sm">{String(value)}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="space-y-2 pt-4 border-t border-slate-700">
                    <button
                      onClick={() => handleExpandNode(selectedNode.id)}
                      className="w-full bg-primary-600 hover:bg-primary-700 text-white py-2 rounded-lg transition-colors"
                    >
                      گسترش گره
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <p>یک گره را انتخاب کنید</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Stats */}
        {graphData && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-slate-400 text-sm mb-1">گره‌ها</div>
              <div className="text-2xl font-bold text-white">{graphData.nodes.length}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-slate-400 text-sm mb-1">یال‌ها</div>
              <div className="text-2xl font-bold text-white">{graphData.edges.length}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-slate-400 text-sm mb-1">مسیر</div>
              <div className="text-2xl font-bold text-white">{graphData.path?.length || 0}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
