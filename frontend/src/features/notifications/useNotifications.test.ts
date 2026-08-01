import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useNotifications } from './useNotifications';

describe('useNotifications', () => {
  it('throws when used outside a NotificationsProvider', () => {
    const { result } = renderHook(() => {
      try {
        return useNotifications();
      } catch (error) {
        return error;
      }
    });

    expect(result.current).toBeInstanceOf(Error);
    expect((result.current as Error).message).toBe(
      'useNotifications must be used within a NotificationsProvider',
    );
  });
});
