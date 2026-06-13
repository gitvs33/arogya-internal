import { describe, it, expect } from 'vitest';

describe('test environment', () => {
  it('works with jsdom', () => {
    expect(document).toBeDefined();
    expect(window).toBeDefined();
  });

  it('can render basic HTML', () => {
    document.body.innerHTML = '<h1>Hello</h1>';
    expect(document.querySelector('h1')).toHaveTextContent('Hello');
  });
});
