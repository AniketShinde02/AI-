export const apiClient = {
  async get(endpoint: string) {
    const res = await fetch(`/api${endpoint}`);
    if (!res.ok) throw new Error('API Error');
    return res.json();
  },
  
  async post(endpoint: string, body: any) {
    const res = await fetch(`/api${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('API Error');
    return res.json();
  }
};
