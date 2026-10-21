import { useEffect, useState } from 'react';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { getErrorMessage } from '@/lib/errors';
import { mcpAdminService } from '@/services/mcpAdminService';
import type { McpTool } from '@/types/assistant';

export function AdminMcpToolsPage() {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const [busyName, setBusyName] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    mcpAdminService
      .list()
      .then((t) => {
        if (cancelled) return;
        setTools(t);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load MCP tools.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const toggle = async (tool: McpTool): Promise<void> => {
    const next = !tool.enabled;
    setToggleError(null);
    setBusyName(tool.name);
    setTools((prev) => prev.map((t) => (t.name === tool.name ? { ...t, enabled: next } : t)));
    try {
      const saved = await mcpAdminService.setEnabled(tool.name, next);
      setTools((prev) => prev.map((t) => (t.name === tool.name ? saved : t)));
    } catch (err) {
      setTools((prev) => prev.map((t) => (t.name === tool.name ? { ...t, enabled: tool.enabled } : t)));
      setToggleError(`Could not update ${tool.name}: ${getErrorMessage(err, 'the change was not saved.')}`);
    } finally {
      setBusyName(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">MCP tools</h1>
        <p className="text-sm text-muted-foreground">
          Tools the assistant can call to read records. Disabling a tool stops the assistant from using it. Each tool is limited to the roles shown.
        </p>
      </div>

      <FormMessage message={error} />
      <FormMessage message={toggleError} />

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading tools...
        </p>
      )}
      {!loading && error && tools.length === 0 && (
        <Button variant="outline" onClick={() => setAttempt((a) => a + 1)}>
          Retry
        </Button>
      )}
      {!loading && !error && tools.length === 0 && <p className="text-muted-foreground">No tools are registered.</p>}
      {tools.length > 0 && (
        <div className="overflow-x-auto rounded-md border bg-background">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <th className="px-3 py-2 font-medium">Tool</th>
                <th className="px-3 py-2 font-medium">Description</th>
                <th className="px-3 py-2 font-medium">Allowed roles</th>
                <th className="px-3 py-2 font-medium">Enabled</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t) => (
                <tr key={t.name} className="border-b last:border-b-0">
                  <td className="px-3 py-2 font-mono text-xs">{t.name}</td>
                  <td className="px-3 py-2">{t.description}</td>
                  <td className="px-3 py-2">
                    <ul className="flex flex-wrap gap-1" aria-label={`Roles for ${t.name}`}>
                      {t.allowed_roles.map((r) => (
                        <li key={r} className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                          {r}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={t.enabled}
                      aria-label={`Enable ${t.name}`}
                      disabled={busyName === t.name}
                      onClick={() => void toggle(t)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60 ${t.enabled ? 'bg-primary' : 'bg-muted-foreground/40'}`}
                    >
                      <span className={`inline-block h-4 w-4 rounded-full bg-background transition-transform ${t.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
