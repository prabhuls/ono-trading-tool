export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Trading Tools Boilerplate
          </h1>
          
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-12">
            A modern full-stack application built with Next.js 15 and FastAPI
          </p>

          <div className="grid md:grid-cols-2 gap-8 mb-12">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                Frontend Stack
              </h2>
              <ul className="space-y-2 text-gray-600 dark:text-gray-300">
                <li>• Next.js 15 with App Router</li>
                <li>• TypeScript for type safety</li>
                <li>• Tailwind CSS for styling</li>
                <li>• React Hook Form for forms</li>
                <li>• Axios for API calls</li>
                <li>• Sentry for error tracking</li>
              </ul>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                Backend Stack
              </h2>
              <ul className="space-y-2 text-gray-600 dark:text-gray-300">
                <li>• FastAPI (Python)</li>
                <li>• PostgreSQL database</li>
                <li>• Redis for caching</li>
                <li>• SQLAlchemy ORM</li>
                <li>• Pydantic validation</li>
                <li>• Structured logging</li>
              </ul>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Getting Started
            </h2>
            <ol className="space-y-3 text-gray-700 dark:text-gray-300">
              <li>
                <strong>1. Start Development:</strong> Run <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-sm">./start-dev.sh</code> to start all services
              </li>
              <li>
                <strong>2. API Documentation:</strong> Visit <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-sm">http://localhost:8000/api/v1/docs</code>
              </li>
              <li>
                <strong>3. Frontend:</strong> Open <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-sm">http://localhost:3000</code>
              </li>
              <li>
                <strong>4. Database:</strong> PostgreSQL runs on <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-sm">localhost:5432</code>
              </li>
            </ol>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Project Structure
              </h3>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
{`trading-tools/
├── server/          # FastAPI backend
│   ├── app/         # Application code
│   ├── alembic/     # Database migrations
│   └── tests/       # Backend tests
├── client/          # Next.js frontend
│   ├── app/         # App router pages
│   ├── components/  # React components
│   └── lib/         # Utilities
└── docs/            # Documentation`}
              </pre>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Key Features
              </h3>
              <ul className="space-y-2 text-gray-600 dark:text-gray-300">
                <li>✓ Type-safe API client with Axios interceptors</li>
                <li>✓ Structured error handling and logging</li>
                <li>✓ Redis caching for performance</li>
                <li>✓ Docker Compose for local development</li>
                <li>✓ Railway-ready deployment configuration</li>
                <li>✓ Comprehensive coding standards</li>
              </ul>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Available Scripts
              </h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded-lg space-y-2 text-sm">
                <p><code>npm run dev</code> - Start development server</p>
                <p><code>npm run build</code> - Build for production</p>
                <p><code>npm run lint</code> - Run ESLint</p>
                <p><code>npm run format</code> - Format with Prettier</p>
                <p><code>npm run type-check</code> - Check TypeScript</p>
              </div>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
            <p className="text-center text-gray-500 dark:text-gray-400">
              Check the <code className="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-sm">/docs</code> directory for detailed documentation
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}