'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Activity, CircleSlash, Clock3, Loader2, Play, TerminalSquare } from 'lucide-react';

type ObserverTicket = {
  assignee: string;
  command: string[];
  exitCode: number | null;
  finishedAt: string;
  humanDecision: null | {
    answer?: string;
    created_at?: string;
    note?: string;
    source?: string;
    previous_status?: string;
  };
  key: string;
  logPath: string;
  logTail: string;
  priority: string;
  startedAt: string;
  status: 'running' | 'done' | 'blocked' | 'failed' | 'pending';
  ticketFile: string;
  title: string;
  worktree: string;
};

type ObserverResponse = {
  runId: string;
  runRoot: string;
  summary: {
    blocked: number;
    done: number;
    failed: number;
    pending: number;
    running: number;
    total: number;
  };
  tickets: ObserverTicket[];
};

const STATUS_LABELS: Record<ObserverTicket['status'], string> = {
  running: 'running',
  done: 'done',
  blocked: 'blocked',
  failed: 'failed',
  pending: 'pending',
};

function formatCommand(command: string[]) {
  return command.length === 0 ? '' : command.join(' ');
}

function formatTime(value: string) {
  if (!value) {
    return '—';
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function QuarterObserver() {
  const searchParams = useSearchParams();
  const run = searchParams.get('run') || '';
  const [data, setData] = useState<ObserverResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState('');

  const endpoint = useMemo(() => {
    const params = new URLSearchParams();
    if (run) {
      params.set('run', run);
    }
    return `/api/quarter-observer${params.toString() ? `?${params.toString()}` : ''}`;
  }, [run]);

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const response = await fetch(endpoint, { cache: 'no-store' });
        const payload = (await response.json()) as ObserverResponse & { error?: string };

        if (!response.ok) {
          throw new Error(payload.error || 'Failed to load observer data');
        }

        if (!active) {
          return;
        }

        setData(payload);
        setError('');
        setUpdatedAt(new Date().toLocaleTimeString());
      } catch (nextError) {
        if (!active) {
          return;
        }
        setError(nextError instanceof Error ? nextError.message : 'Failed to load observer data');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void refresh();
    const interval = window.setInterval(refresh, 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [endpoint]);

  return (
    <section className="observer-shell" aria-label="Quarter run observer">
      <header className="observer-header">
        <div>
          <p className="eyebrow">PR-Watcher</p>
          <h1>Quarter run observer</h1>
          <p className="observer-subtitle">
            {run ? `Run ${run}` : 'Watching the latest queued run'}
          </p>
        </div>
        <div className="observer-meta">
          <span className="observer-chip">
            <Clock3 size={16} aria-hidden="true" />
            {updatedAt ? `Updated ${updatedAt}` : 'Connecting'}
          </span>
          <span className="observer-chip">
            <Activity size={16} aria-hidden="true" />
            {data ? `${data.summary.running} running` : 'Loading'}
          </span>
        </div>
      </header>

      {error ? (
        <div className="observer-alert" role="alert">
          <CircleSlash size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="observer-summary" aria-label="Run summary">
        <div>
          <strong>{data?.summary.total ?? 0}</strong>
          <span>Total</span>
        </div>
        <div>
          <strong>{data?.summary.running ?? 0}</strong>
          <span>Running</span>
        </div>
        <div>
          <strong>{data?.summary.done ?? 0}</strong>
          <span>Done</span>
        </div>
        <div>
          <strong>{data?.summary.blocked ?? 0}</strong>
          <span>Blocked</span>
        </div>
        <div>
          <strong>{data?.summary.failed ?? 0}</strong>
          <span>Failed</span>
        </div>
      </div>

      <div className="observer-run-root">
        <span>Run root</span>
        <code>{data?.runRoot || 'Waiting for run data'}</code>
      </div>

      <div className="observer-list" aria-live="polite">
        {loading && !data ? (
          <div className="observer-loading">
            <Loader2 className="spin" size={18} aria-hidden="true" />
            <span>Loading run state</span>
          </div>
        ) : null}

        {(data?.tickets || []).length === 0 ? (
          <div className="observer-empty">
            <Play size={18} aria-hidden="true" />
            <span>No ticket records found for this run yet.</span>
          </div>
        ) : null}

        {data?.tickets.map((ticket) => (
          <article className="observer-ticket" key={ticket.key}>
            <header className="observer-ticket-head">
              <div>
                <p className="observer-ticket-key">{ticket.key}</p>
                <h2>{ticket.title}</h2>
              </div>
              <span className="observer-status" data-status={ticket.status}>
                {STATUS_LABELS[ticket.status]}
              </span>
            </header>

            <div className="observer-ticket-meta">
              <div>
                <span>Assignee</span>
                <strong>{ticket.assignee || 'unassigned'}</strong>
              </div>
              <div>
                <span>Priority</span>
                <strong>{ticket.priority || 'Unspecified'}</strong>
              </div>
              <div>
                <span>Started</span>
                <strong>{formatTime(ticket.startedAt)}</strong>
              </div>
              <div>
                <span>Finished</span>
                <strong>{formatTime(ticket.finishedAt)}</strong>
              </div>
            </div>

            <div className="observer-ticket-command">
              <span>Command</span>
              <code>{formatCommand(ticket.command) || 'No command recorded'}</code>
            </div>

            <div className="observer-ticket-command">
              <span>Log</span>
              <code>{ticket.logPath || 'No log path recorded'}</code>
            </div>

            {ticket.humanDecision ? (
              <div className="observer-decision">
                <span>Human decision</span>
                <code>{ticket.humanDecision.answer || 'pending'}</code>
              </div>
            ) : null}

            <pre className="observer-log" aria-label={`${ticket.key} log tail`}>
              {ticket.logTail || 'No log output yet.'}
            </pre>

            <footer className="observer-ticket-footer">
              <span>Exit code: {ticket.exitCode === null ? 'n/a' : ticket.exitCode}</span>
              {ticket.worktree ? (
                <span className="observer-inline">
                  <TerminalSquare size={16} aria-hidden="true" />
                  {ticket.worktree}
                </span>
              ) : null}
              <span>{ticket.logPath}</span>
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}
