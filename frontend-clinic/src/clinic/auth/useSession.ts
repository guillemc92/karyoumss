import { useContext } from 'react';
import { SessionContext, type SessionContextValue } from './SessionProvider';

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSession debe usarse dentro de <SessionProvider>');
  }
  return ctx;
}
