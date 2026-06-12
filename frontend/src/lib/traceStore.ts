export interface TraceEvent {
  id: string;
  icon: string;
  text: string;
  timestamp: number;
}

class TraceStore {
  private events: TraceEvent[] = [];
  private maxEvents = 50;
  private listeners: ((events: TraceEvent[]) => void)[] = [];

  addTrace(icon: string, text: string) {
    const event: TraceEvent = {
      id: Math.random().toString(36).substring(7),
      icon,
      text,
      timestamp: Date.now()
    };
    
    // Add to end of list (bottom) for a timeline that grows downwards
    this.events = [...this.events, event].slice(-this.maxEvents);
    this.notify();
  }

  getEvents() {
    return this.events;
  }

  subscribe(listener: (events: TraceEvent[]) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach(l => l(this.events));
  }

  clear() {
    this.events = [];
    this.notify();
  }
}

export const traceStore = new TraceStore();
