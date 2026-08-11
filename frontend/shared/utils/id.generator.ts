/**
 * ID Generator Utility
 * 
 * Generates unique IDs for various purposes
 */

export class IdGenerator {
  private static counter: Record<string, number> = {};

  static generate(prefix: string = 'id'): string {
    const count = (this.counter[prefix] || 0) + 1;
    this.counter[prefix] = count;
    
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    
    return `${prefix}_${timestamp}_${random}_${count}`;
  }

  static reset(prefix?: string): void {
    if (prefix) {
      delete this.counter[prefix];
    } else {
      this.counter = {};
    }
  }
}
