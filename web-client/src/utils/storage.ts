export class Storage {
  static get(key: string): string | null {
    return localStorage.getItem(key);
  }

  static set(key: string, value: string): void {
    localStorage.setItem(key, value);
  }

  static remove(key: string): void {
    localStorage.removeItem(key);
  }

  static getJSON<T>(key: string): T | null {
    const value = this.get(key);
    if (value) {
      try {
        return JSON.parse(value);
      } catch {
        return null;
      }
    }
    return null;
  }

  static setJSON(key: string, value: any): void {
    this.set(key, JSON.stringify(value));
  }
}