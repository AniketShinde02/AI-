export interface NexusLog {
  id: string;
  level: 'info' | 'warn' | 'error' | 'debug' | 'ai';
  message: string;
  timestamp: number;
  data?: any;
}

class LogStore {
  private logs: NexusLog[] = [];
  private maxLogs = 50; // Keep it minimal as requested
  private listeners: ((logs: NexusLog[]) => void)[] = [];

  addLog(level: NexusLog['level'], message: string, data?: any) {
    // Basic de-spamming: if the last log is identical and recent, skip or update?
    // For now, just a simple limit.
    const log: NexusLog = {
      id: Math.random().toString(36).slice(2, 9),
      level,
      message,
      timestamp: Date.now(),
      data
    };
    
    this.logs = [log, ...this.logs].slice(0, this.maxLogs);
    this.notify();
  }

  getLogs() {
    return this.logs;
  }

  subscribe(listener: (logs: NexusLog[]) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach(l => l(this.logs));
  }

  clear() {
    this.logs = [];
    this.notify();
  }
}

export const logStore = new LogStore();
