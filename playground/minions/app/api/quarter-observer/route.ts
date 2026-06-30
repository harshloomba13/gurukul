import { NextRequest, NextResponse } from 'next/server';
import fs from 'node:fs/promises';
import path from 'node:path';

export const runtime = 'nodejs';

type TicketSnapshot = {
  assignee?: string;
  command?: string[];
  exit_code?: number;
  finished_at?: string;
  human_decision?: {
    answer?: string;
    created_at?: string;
    note?: string;
    source?: string;
    previous_status?: string;
  };
  log?: string;
  priority?: string;
  started_at?: string;
  status?: string;
  ticket_file?: string;
  title?: string;
  worktree?: string;
};

type QuarterState = {
  tickets?: Record<string, TicketSnapshot>;
};

type Summary = {
  total: number;
  running: number;
  done: number;
  blocked: number;
  failed: number;
  pending: number;
};

const QUARTER_RUNS_DIR = path.resolve(process.cwd(), '.runs', 'quarter');
const LOG_LINE_LIMIT = 120;
const RUN_ID_PATTERN = /^\d{8}T\d{6}Z$/;

async function readJsonFile<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

async function getLatestRunId(): Promise<string | null> {
  try {
    const entries = await fs.readdir(QUARTER_RUNS_DIR, { withFileTypes: true });
    const runIds = entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .filter((name) => RUN_ID_PATTERN.test(name))
      .sort()
      .reverse();
    return runIds[0] || null;
  } catch {
    return null;
  }
}

async function readLogTail(logPath: string): Promise<string> {
  try {
    const raw = await fs.readFile(logPath, 'utf8');
    const lines = raw.split(/\r?\n/).filter(Boolean);
    return lines.slice(-LOG_LINE_LIMIT).join('\n');
  } catch {
    return '';
  }
}

function isRunTicket(record: TicketSnapshot, runRoot: string) {
  return typeof record.log === 'string' && record.log.startsWith(runRoot);
}

function keyFromLogFile(fileName: string) {
  return fileName.replace(/\.log$/, '').toUpperCase();
}

function statusFromLogTail(logTail: string): string {
  const lowered = logTail.toLowerCase();
  if (
    lowered.includes('draft pr created')
    || lowered.includes('existing pr handed off')
    || lowered.includes('no remaining blockers')
  ) {
    return 'done';
  }
  if (lowered.includes('minion_blocked') || lowered.includes('blocked')) {
    return 'blocked';
  }
  if (lowered.includes('failed') || lowered.includes('error:')) {
    return 'failed';
  }
  return 'pending';
}

async function readRunLogTickets(runRoot: string) {
  try {
    const entries = await fs.readdir(runRoot, { withFileTypes: true });
    const logFiles = entries
      .filter((entry) => entry.isFile() && entry.name.endsWith('.log'))
      .map((entry) => entry.name)
      .sort();

    return Promise.all(
      logFiles.map(async (fileName) => {
        const logPath = path.join(runRoot, fileName);
        const logTail = await readLogTail(logPath);
        const key = keyFromLogFile(fileName);
        return {
          key,
          assignee: '',
          command: [],
          exitCode: null,
          finishedAt: '',
          humanDecision: null,
          logPath,
          logTail,
          priority: '',
          startedAt: '',
          status: statusFromLogTail(logTail),
          ticketFile: '',
          title: key,
          worktree: '',
        };
      }),
    );
  } catch {
    return [];
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const requestedRunId = searchParams.get('run');
  const runId = requestedRunId || (await getLatestRunId());

  if (!runId) {
    return NextResponse.json(
      { error: 'No quarter run has been recorded yet.' },
      { status: 404 },
    );
  }

  const runRoot = path.join(QUARTER_RUNS_DIR, runId);
  const statePath = path.join(QUARTER_RUNS_DIR, 'state.json');
  const [state, runExists] = await Promise.all([
    readJsonFile<QuarterState>(statePath),
    fs
      .stat(runRoot)
      .then((stat) => stat.isDirectory())
      .catch(() => false),
  ]);

  if (!runExists) {
    return NextResponse.json(
      { error: `Quarter run not found: ${runId}` },
      { status: 404 },
    );
  }

  let tickets = await Promise.all(
    Object.entries(state?.tickets || {})
      .filter(([, record]) => isRunTicket(record, runRoot))
      .map(async ([key, record]) => ({
        key,
        assignee: record.assignee || '',
        command: Array.isArray(record.command) ? record.command : [],
        exitCode: typeof record.exit_code === 'number' ? record.exit_code : null,
        finishedAt: record.finished_at || '',
        humanDecision: record.human_decision || null,
        logPath: record.log || '',
        logTail: record.log ? await readLogTail(record.log) : '',
        priority: record.priority || '',
        startedAt: record.started_at || '',
        status: record.status || 'pending',
        ticketFile: record.ticket_file || '',
        title: record.title || key,
        worktree: record.worktree || '',
      })),
  );
  if (tickets.length === 0) {
    tickets = await readRunLogTickets(runRoot);
  }

  const summary: Summary = tickets.reduce(
    (acc, ticket) => {
      acc.total += 1;
      switch (ticket.status) {
        case 'running':
          acc.running += 1;
          break;
        case 'done':
          acc.done += 1;
          break;
        case 'blocked':
          acc.blocked += 1;
          break;
        case 'failed':
          acc.failed += 1;
          break;
        default:
          acc.pending += 1;
          break;
      }
      return acc;
    },
    {
      total: 0,
      running: 0,
      done: 0,
      blocked: 0,
      failed: 0,
      pending: 0,
    } as Summary,
  );

  return NextResponse.json({
    runId,
    runRoot,
    summary,
    tickets,
  });
}
