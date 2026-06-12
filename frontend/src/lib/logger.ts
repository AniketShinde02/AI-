import { logStore } from './logStore';

type LogLevel = 'info' | 'warn' | 'error' | 'debug' | 'ai';

class NexusLogger {
  private prefix = '[Nexus]';

  private format(level: LogLevel, message: string, data?: any) {
    const timestamp = new Date().toLocaleTimeString();
    const color = this.getColor(level);
    const label = `%c${this.prefix} [${level.toUpperCase()}] ${timestamp}:`;
    
    // Console output for developers
    if (data) {
      console.log(label, color, message, data);
    } else {
      console.log(label, color, message);
    }

    // Push to UI log store
    logStore.addLog(level, message, data);
  }

  private getColor(level: LogLevel): string {
    switch (level) {
      case 'info': return 'color: #6366f1; font-weight: bold;';
      case 'warn': return 'color: #fbbf24; font-weight: bold;';
      case 'error': return 'color: #ef4444; font-weight: bold;';
      case 'debug': return 'color: #94a3b8; font-weight: normal;';
      case 'ai': return 'color: #a855f7; font-weight: bold;';
      default: return '';
    }
  }

  info(msg: string, data?: any) { this.format('info', msg, data); }
  warn(msg: string, data?: any) { this.format('warn', msg, data); }
  error(msg: string, data?: any) { this.format('error', msg, data); }
  debug(msg: string, data?: any) { this.format('debug', msg, data); }
  ai(msg: string, data?: any) { this.format('ai', msg, data); }

  /**
   * Logs API interactions specifically to help debug connectivity.
   */
  api(method: string, url: string, status?: number, data?: any) {
    const statusMsg = status ? `[${status}]` : '[PENDING]';
    this.info(`API ${method} ${url} ${statusMsg}`, data);
  }
}

export const logger = new NexusLogger();
