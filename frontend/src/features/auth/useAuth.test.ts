import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useAuth } from './useAuth';

describe('useAuth', () => {
  it('throws when used outside an AuthProvider', () => {
    // renderHook still needs a real render pass for React's hook dispatcher
    // to be active - calling useAuth() as a bare function crashes on "no
    // dispatcher" before ever reaching our own guard clause.
    const { result } = renderHook(() => {
      try {
        return useAuth();
      } catch (error) {
        return error;
      }
    });

    expect(result.current).toBeInstanceOf(Error);
    expect((result.current as Error).message).toBe('useAuth must be used within an AuthProvider');
  });
});
