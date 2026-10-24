/**
 * Admin users store — reducer puro + Context para que los componentes lean
 * el estado vía hook. No usa Zustand para evitar deps extra en F4/F5; cuando
 * el bounded context crezca se puede migrar sin tocar la API de los componentes.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react';
import {
  AdminUser,
  AdminUserDraft,
  AdminUserUpdate,
  AuditLogEntry,
} from '../types/adminUser';
import { AdminClient, adminClient } from '../api/adminClient';

export type LoadStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AdminUsersState {
  users: AdminUser[];
  status: LoadStatus;
  errorMessage: string | null;
  /** id del usuario cuyo historial se está mostrando (modal abierto). */
  historyOpenFor: string | null;
  history: AuditLogEntry[];
  historyStatus: LoadStatus;
}

type Action =
  | { type: 'load_start' }
  | { type: 'load_success'; users: AdminUser[] }
  | { type: 'load_error'; message: string }
  | { type: 'upsert'; user: AdminUser }
  | { type: 'remove'; id: string }
  | { type: 'history_open'; id: string }
  | { type: 'history_loaded'; entries: AuditLogEntry[] }
  | { type: 'history_error'; message: string }
  | { type: 'history_close' }
  | { type: 'reset' };

const initialState: AdminUsersState = {
  users: [],
  status: 'idle',
  errorMessage: null,
  historyOpenFor: null,
  history: [],
  historyStatus: 'idle',
};

function reducer(state: AdminUsersState, action: Action): AdminUsersState {
  switch (action.type) {
    case 'load_start':
      return { ...state, status: 'loading', errorMessage: null };
    case 'load_success':
      return { ...state, status: 'success', users: action.users, errorMessage: null };
    case 'load_error':
      return { ...state, status: 'error', errorMessage: action.message };
    case 'upsert': {
      const idx = state.users.findIndex((u) => u.id === action.user.id);
      const users =
        idx >= 0
          ? state.users.map((u) => (u.id === action.user.id ? action.user : u))
          : [...state.users, action.user];
      return { ...state, users };
    }
    case 'remove':
      return {
        ...state,
        users: state.users.filter((u) => u.id !== action.id),
      };
    case 'history_open':
      return {
        ...state,
        historyOpenFor: action.id,
        history: [],
        historyStatus: 'loading',
      };
    case 'history_loaded':
      return { ...state, history: action.entries, historyStatus: 'success' };
    case 'history_error':
      return { ...state, historyStatus: 'error' };
    case 'history_close':
      return {
        ...state,
        historyOpenFor: null,
        history: [],
        historyStatus: 'idle',
      };
    case 'reset':
      return initialState;
    default:
      return state;
  }
}

export interface AdminUsersStore {
  state: AdminUsersState;
  load(): Promise<void>;
  createUser(draft: AdminUserDraft): Promise<AdminUser>;
  updateUser(id: string, patch: AdminUserUpdate): Promise<AdminUser>;
  deleteUser(id: string): Promise<void>;
  openHistory(id: string): Promise<void>;
  closeHistory(): void;
}

const AdminUsersContext = createContext<AdminUsersStore | null>(null);

export interface AdminUsersProviderProps {
  children: ReactNode;
  /** Permite inyectar un cliente falso (MSW + tests). */
  client?: AdminClient;
}

export function AdminUsersProvider({
  children,
  client = adminClient,
}: AdminUsersProviderProps) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const load = useCallback(async () => {
    dispatch({ type: 'load_start' });
    try {
      const users = await client.list();
      dispatch({ type: 'load_success', users });
    } catch (err) {
      dispatch({
        type: 'load_error',
        message: err instanceof Error ? err.message : 'Error desconocido',
      });
    }
  }, [client]);

  const createUser = useCallback(
    async (draft: AdminUserDraft) => {
      const user = await client.create(draft);
      dispatch({ type: 'upsert', user });
      return user;
    },
    [client],
  );

  const updateUser = useCallback(
    async (id: string, patch: AdminUserUpdate) => {
      const user = await client.update(id, patch);
      dispatch({ type: 'upsert', user });
      return user;
    },
    [client],
  );

  const deleteUser = useCallback(
    async (id: string) => {
      await client.softDelete(id);
      dispatch({ type: 'remove', id });
    },
    [client],
  );

  const openHistory = useCallback(
    async (id: string) => {
      dispatch({ type: 'history_open', id });
      try {
        const entries = await client.history(id);
        dispatch({ type: 'history_loaded', entries });
      } catch {
        dispatch({ type: 'history_error', message: 'No se pudo cargar el historial' });
      }
    },
    [client],
  );

  const closeHistory = useCallback(() => {
    dispatch({ type: 'history_close' });
  }, []);

  const store = useMemo<AdminUsersStore>(
    () => ({ state, load, createUser, updateUser, deleteUser, openHistory, closeHistory }),
    [state, load, createUser, updateUser, deleteUser, openHistory, closeHistory],
  );

  return <AdminUsersContext.Provider value={store}>{children}</AdminUsersContext.Provider>;
}

export function useAdminUsers(): AdminUsersStore {
  const ctx = useContext(AdminUsersContext);
  if (!ctx) {
    throw new Error('useAdminUsers debe usarse dentro de <AdminUsersProvider>');
  }
  return ctx;
}