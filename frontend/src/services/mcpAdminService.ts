import api from './api';
import type { McpTool } from '@/types/assistant';

function normaliseTool(raw: McpTool): McpTool {
  return { ...raw, description: raw.description ?? '', allowed_roles: raw.allowed_roles ?? [], enabled: Boolean(raw.enabled) };
}

export const mcpAdminService = {
  async list(): Promise<McpTool[]> {
    const { data } = await api.get<McpTool[]>('/admin/mcp-tools');
    return (data ?? []).map(normaliseTool);
  },

  async setEnabled(name: string, enabled: boolean): Promise<McpTool> {
    const { data } = await api.put<McpTool>(`/admin/mcp-tools/${encodeURIComponent(name)}`, { enabled });
    return normaliseTool(data);
  },
};
