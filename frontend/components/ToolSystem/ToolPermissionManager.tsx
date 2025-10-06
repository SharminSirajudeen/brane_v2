/**
 * BRANE Tool Permission Manager Component
 * UI for granting, managing, and monitoring tool permissions for Neurons
 */

import React, { useState, useEffect } from 'react';
import {
  Shield,
  Lock,
  Unlock,
  AlertTriangle,
  Check,
  X,
  Clock,
  Zap,
  Eye,
  Settings,
  ChevronRight,
  Search,
  Filter,
  RefreshCw,
  Activity,
  Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { format, formatDistanceToNow } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { toolApi } from '@/api/tools';
import { Tool, Permission, PermissionRequest, ExecutionStatus } from '@/types/tools';

interface ToolPermissionManagerProps {
  neuronId: string;
  neuronName: string;
  userId: string;
}

const PERMISSION_SCOPES = [
  { id: 'read', label: 'Read', icon: Eye, description: 'View and retrieve data' },
  { id: 'write', label: 'Write', icon: Lock, description: 'Modify and create data' },
  { id: 'execute', label: 'Execute', icon: Zap, description: 'Run operations' },
  { id: 'delete', label: 'Delete', icon: X, description: 'Remove data' },
];

const TOOL_CATEGORIES = [
  { id: 'file_system', label: 'File System', icon: '📁' },
  { id: 'network', label: 'Network', icon: '🌐' },
  { id: 'hardware', label: 'Hardware', icon: '🔧' },
  { id: 'services', label: 'Services', icon: '☁️' },
  { id: 'system', label: 'System', icon: '⚙️' },
  { id: 'data_processing', label: 'Data Processing', icon: '📊' },
];

export const ToolPermissionManager: React.FC<ToolPermissionManagerProps> = ({
  neuronId,
  neuronName,
  userId
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [showPermissionModal, setShowPermissionModal] = useState(false);
  const [permissionScopes, setPermissionScopes] = useState<string[]>(['execute']);
  const [expiresInHours, setExpiresInHours] = useState<number | null>(null);
  const [maxDailyUses, setMaxDailyUses] = useState<number | null>(null);
  const [requireConfirmation, setRequireConfirmation] = useState(false);
  const queryClient = useQueryClient();

  // Fetch available tools
  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ['tools', searchQuery, selectedCategory],
    queryFn: () => toolApi.discoverTools({
      query: searchQuery,
      categories: selectedCategory ? [selectedCategory] : undefined,
      only_permitted: false
    })
  });

  // Fetch current permissions
  const { data: permissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['permissions', neuronId],
    queryFn: () => toolApi.getNeuronPermissions(neuronId)
  });

  // Grant permission mutation
  const grantMutation = useMutation({
    mutationFn: (request: PermissionRequest) => toolApi.grantPermission(request),
    onSuccess: () => {
      toast.success('Permission granted successfully');
      queryClient.invalidateQueries({ queryKey: ['permissions', neuronId] });
      setShowPermissionModal(false);
      resetPermissionForm();
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to grant permission');
    }
  });

  // Revoke permission mutation
  const revokeMutation = useMutation({
    mutationFn: ({ permissionId, reason }: { permissionId: string; reason: string }) =>
      toolApi.revokePermission(permissionId, reason),
    onSuccess: () => {
      toast.success('Permission revoked');
      queryClient.invalidateQueries({ queryKey: ['permissions', neuronId] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to revoke permission');
    }
  });

  const resetPermissionForm = () => {
    setSelectedTool(null);
    setPermissionScopes(['execute']);
    setExpiresInHours(null);
    setMaxDailyUses(null);
    setRequireConfirmation(false);
  };

  const handleGrantPermission = () => {
    if (!selectedTool) return;

    const request: PermissionRequest = {
      tool_id: selectedTool.id,
      neuron_id: neuronId,
      scopes: permissionScopes,
      expires_in_hours: expiresInHours,
      max_daily_uses: maxDailyUses,
      require_confirmation: requireConfirmation
    };

    grantMutation.mutate(request);
  };

  const getPrivacyTierBadge = (tier: number) => {
    const badges = {
      0: { label: 'Local', color: 'bg-green-500' },
      1: { label: 'Private', color: 'bg-yellow-500' },
      2: { label: 'Public', color: 'bg-red-500' }
    };
    const badge = badges[tier as keyof typeof badges];
    return (
      <span className={`px-2 py-1 text-xs rounded-full text-white ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Shield className="w-8 h-8 text-blue-500" />
            <div>
              <h2 className="text-2xl font-bold text-white">Tool Permissions</h2>
              <p className="text-gray-400">Manage {neuronName}'s access to system tools</p>
            </div>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['tools'] })}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Search and Filters */}
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tools..."
              className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={selectedCategory || ''}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {TOOL_CATEGORIES.map(cat => (
              <option key={cat.id} value={cat.id}>
                {cat.icon} {cat.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Current Permissions */}
      <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
          <Lock className="w-5 h-5 mr-2 text-green-500" />
          Active Permissions ({permissions?.length || 0})
        </h3>

        {permissionsLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : permissions && permissions.length > 0 ? (
          <div className="space-y-3">
            {permissions.map((permission: Permission) => (
              <motion.div
                key={permission.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-lg p-4 border border-gray-700"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center">
                      {permission.tool_icon || '🔧'}
                    </div>
                    <div>
                      <h4 className="font-semibold text-white">{permission.tool_name}</h4>
                      <div className="flex items-center space-x-2 mt-1">
                        {permission.scopes.map(scope => (
                          <span key={scope} className="px-2 py-0.5 bg-blue-900 text-blue-300 text-xs rounded">
                            {scope}
                          </span>
                        ))}
                        {permission.expires_at && (
                          <span className="text-xs text-gray-400 flex items-center">
                            <Clock className="w-3 h-3 mr-1" />
                            Expires {formatDistanceToNow(new Date(permission.expires_at), { addSuffix: true })}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {permission.current_uses && permission.max_total_uses && (
                      <span className="text-sm text-gray-400">
                        {permission.current_uses} / {permission.max_total_uses} uses
                      </span>
                    )}
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to revoke this permission?')) {
                          revokeMutation.mutate({
                            permissionId: permission.id,
                            reason: 'User requested revocation'
                          });
                        }
                      }}
                      className="p-2 rounded-lg bg-red-900 hover:bg-red-800 transition-colors"
                    >
                      <X className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">No active permissions</p>
        )}
      </div>

      {/* Available Tools */}
      <div className="bg-gray-900 rounded-lg p-6 border border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
          <Settings className="w-5 h-5 mr-2 text-blue-500" />
          Available Tools
        </h3>

        {toolsLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {toolsData?.tools.map((tool: Tool) => (
              <motion.div
                key={tool.id}
                whileHover={{ scale: 1.02 }}
                className={`bg-gray-800 rounded-lg p-4 border cursor-pointer transition-all ${
                  tool.permitted ? 'border-green-700' : 'border-gray-700 hover:border-blue-600'
                }`}
                onClick={() => {
                  if (!tool.permitted) {
                    setSelectedTool(tool);
                    setShowPermissionModal(true);
                  }
                }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center text-2xl">
                      {tool.icon || '🔧'}
                    </div>
                    <div>
                      <h4 className="font-semibold text-white">{tool.display_name}</h4>
                      <span className="text-xs text-gray-400">{tool.category}</span>
                    </div>
                  </div>
                  {tool.permitted && (
                    <Check className="w-5 h-5 text-green-500" />
                  )}
                </div>

                <p className="text-sm text-gray-400 mb-3 line-clamp-2">{tool.description}</p>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {getPrivacyTierBadge(tool.privacy_tier)}
                    {tool.dangerous && (
                      <span className="px-2 py-1 text-xs rounded-full bg-orange-900 text-orange-300">
                        <AlertTriangle className="w-3 h-3 inline mr-1" />
                        Dangerous
                      </span>
                    )}
                  </div>
                  {!tool.permitted && (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Permission Grant Modal */}
      <AnimatePresence>
        {showPermissionModal && selectedTool && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowPermissionModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-900 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-800"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-bold text-white mb-4">Grant Permission</h3>

              {/* Tool Info */}
              <div className="bg-gray-800 rounded-lg p-4 mb-6">
                <div className="flex items-start space-x-3">
                  <div className="w-12 h-12 bg-gray-700 rounded-lg flex items-center justify-center text-2xl">
                    {selectedTool.icon || '🔧'}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-white">{selectedTool.display_name}</h4>
                    <p className="text-sm text-gray-400 mt-1">{selectedTool.description}</p>
                    <div className="flex items-center space-x-3 mt-2">
                      {getPrivacyTierBadge(selectedTool.privacy_tier)}
                      {selectedTool.dangerous && (
                        <span className="text-orange-400 text-sm flex items-center">
                          <AlertTriangle className="w-4 h-4 mr-1" />
                          This tool can perform dangerous operations
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Permission Scopes */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-3">Permission Scopes</label>
                <div className="grid grid-cols-2 gap-3">
                  {PERMISSION_SCOPES.map(scope => (
                    <label
                      key={scope.id}
                      className={`flex items-center p-3 rounded-lg border cursor-pointer transition-all ${
                        permissionScopes.includes(scope.id)
                          ? 'bg-blue-900 border-blue-700'
                          : 'bg-gray-800 border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={permissionScopes.includes(scope.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setPermissionScopes([...permissionScopes, scope.id]);
                          } else {
                            setPermissionScopes(permissionScopes.filter(s => s !== scope.id));
                          }
                        }}
                        className="sr-only"
                      />
                      <scope.icon className="w-5 h-5 mr-3 text-blue-400" />
                      <div>
                        <p className="text-white font-medium">{scope.label}</p>
                        <p className="text-xs text-gray-400">{scope.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Constraints */}
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Expiration (hours)
                  </label>
                  <input
                    type="number"
                    value={expiresInHours || ''}
                    onChange={(e) => setExpiresInHours(e.target.value ? parseInt(e.target.value) : null)}
                    placeholder="Never expires"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max daily uses
                  </label>
                  <input
                    type="number"
                    value={maxDailyUses || ''}
                    onChange={(e) => setMaxDailyUses(e.target.value ? parseInt(e.target.value) : null)}
                    placeholder="Unlimited"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={requireConfirmation}
                    onChange={(e) => setRequireConfirmation(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-700 bg-gray-800 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="text-gray-300">Require confirmation for each execution</span>
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowPermissionModal(false)}
                  className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGrantPermission}
                  disabled={permissionScopes.length === 0 || grantMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {grantMutation.isPending ? 'Granting...' : 'Grant Permission'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};