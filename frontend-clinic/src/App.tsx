import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from './clinic/auth';
import { AppRoutes } from './routes';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const useMsw = import.meta.env.VITE_USE_MSW === 'true';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider forceAnalystOnMount={useMsw}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </SessionProvider>
    </QueryClientProvider>
  );
}

export default App;
