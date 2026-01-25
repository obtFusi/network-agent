import { NavLink, Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import { useEventStream } from '@/hooks/useEventStream';

interface NavItemProps {
  to: string;
  children: React.ReactNode;
}

function NavItem({ to, children }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors',
          isActive
            ? 'bg-blue-100 text-blue-800'
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        )
      }
    >
      {children}
    </NavLink>
  );
}

export function Layout() {
  const { connected } = useEventStream();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                CI/CD Dashboard
              </h1>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2 text-sm">
                <span
                  className={clsx(
                    'w-2 h-2 rounded-full',
                    connected ? 'bg-green-500' : 'bg-red-500'
                  )}
                />
                <span className="text-gray-600">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Sidebar */}
          <aside className="w-64 flex-shrink-0">
            <nav className="space-y-1">
              <NavItem to="/">Pipelines</NavItem>
              <NavItem to="/approvals">Approvals</NavItem>
            </nav>
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
