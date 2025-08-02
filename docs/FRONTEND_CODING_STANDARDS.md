# Frontend Coding Standards

This document outlines the coding standards and best practices for the Next.js/TypeScript frontend of the Trading Tools platform.

## Table of Contents
- [TypeScript Standards](#typescript-standards)
- [React/Next.js Conventions](#reactnextjs-conventions)
- [Project Structure](#project-structure)
- [Component Standards](#component-standards)
- [State Management](#state-management)
- [Styling Standards](#styling-standards)
- [API Integration](#api-integration)
- [Testing Standards](#testing-standards)
- [Performance Guidelines](#performance-guidelines)
- [Accessibility Standards](#accessibility-standards)

## TypeScript Standards

### TypeScript Configuration

Use strict TypeScript settings in `tsconfig.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Type Definitions

1. **Prefer interfaces over types** for object shapes:
   ```typescript
   // Good
   interface User {
     id: string;
     email: string;
     username: string;
   }
   
   // Use type for unions, intersections, or aliases
   type Status = 'active' | 'inactive' | 'pending';
   type ID = string | number;
   ```

2. **Always define return types**:
   ```typescript
   // Good
   function calculateTotal(items: Item[]): number {
     return items.reduce((sum, item) => sum + item.price, 0);
   }
   
   // Bad
   function calculateTotal(items: Item[]) {
     return items.reduce((sum, item) => sum + item.price, 0);
   }
   ```

3. **Use generic types appropriately**:
   ```typescript
   // Good
   interface ApiResponse<T> {
     data: T;
     status: number;
     message: string;
   }
   
   function fetchData<T>(url: string): Promise<ApiResponse<T>> {
     // Implementation
   }
   ```

### Naming Conventions

1. **Files and folders**: Use kebab-case
   ```
   user-profile.tsx
   api-client.ts
   use-auth.ts
   ```

2. **Components**: Use PascalCase
   ```typescript
   export function UserProfile() { }
   export function TradingDashboard() { }
   ```

3. **Variables and functions**: Use camelCase
   ```typescript
   const userName = 'John';
   function calculatePortfolioValue() { }
   ```

4. **Constants**: Use UPPER_SNAKE_CASE
   ```typescript
   const API_BASE_URL = 'https://api.example.com';
   const MAX_RETRY_ATTEMPTS = 3;
   ```

5. **Enums**: Use PascalCase with UPPER_SNAKE_CASE values
   ```typescript
   enum UserRole {
     ADMIN = 'ADMIN',
     USER = 'USER',
     GUEST = 'GUEST'
   }
   ```

## React/Next.js Conventions

### Component Design Principles

1. **Single Responsibility Principle (SRP)**:
   ```typescript
   // Bad - Component doing too many things
   function UserDashboard() {
     const [user, setUser] = useState();
     const [posts, setPosts] = useState();
     const [notifications, setNotifications] = useState();
     const [isEditing, setIsEditing] = useState(false);
     
     // Fetching logic
     useEffect(() => { /* fetch user */ }, []);
     useEffect(() => { /* fetch posts */ }, []);
     useEffect(() => { /* fetch notifications */ }, []);
     
     // Handlers for different concerns
     const handleUpdateProfile = () => { /* ... */ };
     const handleCreatePost = () => { /* ... */ };
     const handleDismissNotification = () => { /* ... */ };
     
     return (
       <div>
         {/* 200+ lines of mixed UI */}
       </div>
     );
   }
   
   // Good - Separate components with single responsibilities
   function UserDashboard() {
     return (
       <div className="dashboard">
         <UserProfile />
         <UserPosts />
         <NotificationList />
       </div>
     );
   }
   
   function UserProfile() {
     const { user, updateUser } = useUser();
     return <ProfileCard user={user} onUpdate={updateUser} />;
   }
   
   function UserPosts() {
     const { posts, createPost } = usePosts();
     return <PostList posts={posts} onCreate={createPost} />;
   }
   ```

2. **Everything that can be a component should be a component**:
   ```typescript
   // Bad - Everything in one component
   function ProductCard({ product }) {
     return (
       <div className="card">
         <img src={product.image} alt={product.name} />
         <h3>{product.name}</h3>
         <p>{product.description}</p>
         <div className="price">
           <span className="currency">$</span>
           <span className="amount">{product.price}</span>
         </div>
         <div className="rating">
           {[...Array(5)].map((_, i) => (
             <Star key={i} filled={i < product.rating} />
           ))}
         </div>
         <button className="add-to-cart">Add to Cart</button>
       </div>
     );
   }
   
   // Good - Broken into smaller components
   function ProductCard({ product }) {
     return (
       <Card>
         <ProductImage src={product.image} alt={product.name} />
         <ProductInfo name={product.name} description={product.description} />
         <ProductPrice price={product.price} />
         <ProductRating rating={product.rating} />
         <AddToCartButton productId={product.id} />
       </Card>
     );
   }
   ```

3. **Keep components small** (max 100-150 lines):
   - If a component exceeds 100 lines, break it down
   - Extract complex logic into custom hooks
   - Extract repeated UI patterns into sub-components

4. **File length limits** (max 300-500 lines):
   - Split large files into multiple components
   - One main component per file
   - Related small components can be in the same file
   - If file exceeds 300 lines, refactor into separate files

### Component Structure

1. **Use functional components** with hooks:
   ```typescript
   // Good
   export function UserProfile({ userId }: UserProfileProps) {
     const [user, setUser] = useState<User | null>(null);
     
     useEffect(() => {
       fetchUser(userId).then(setUser);
     }, [userId]);
     
     return <div>{user?.name}</div>;
   }
   
   // Don't use class components
   ```

2. **Component file structure**:
   ```typescript
   // user-profile.tsx
   import { useState, useEffect } from 'react';
   import { useRouter } from 'next/navigation';
   
   // Types
   interface UserProfileProps {
     userId: string;
     onUpdate?: (user: User) => void;
   }
   
   // Component
   export function UserProfile({ userId, onUpdate }: UserProfileProps) {
     // Hooks
     const router = useRouter();
     const [user, setUser] = useState<User | null>(null);
     const [loading, setLoading] = useState(true);
     
     // Effects
     useEffect(() => {
       // Effect logic
     }, [userId]);
     
     // Handlers
     const handleUpdate = async () => {
       // Handler logic
     };
     
     // Render
     if (loading) return <LoadingSpinner />;
     
     return (
       <div>
         {/* Component JSX */}
       </div>
     );
   }
   ```

### Function Design Principles

1. **Single Responsibility for Functions**:
   ```typescript
   // Bad - Function doing multiple things
   function handleFormSubmit(formData: FormData) {
     // Validate
     if (!formData.email || !formData.password) {
       setError('Missing fields');
       return;
     }
     if (!isValidEmail(formData.email)) {
       setError('Invalid email');
       return;
     }
     
     // Transform data
     const payload = {
       email: formData.email.toLowerCase(),
       password: hashPassword(formData.password),
       timestamp: Date.now()
     };
     
     // Submit
     fetch('/api/auth', { method: 'POST', body: JSON.stringify(payload) })
       .then(res => res.json())
       .then(data => {
         localStorage.setItem('token', data.token);
         router.push('/dashboard');
       });
   }
   
   // Good - Each function has one responsibility
   function validateFormData(formData: FormData): ValidationResult {
     if (!formData.email || !formData.password) {
       return { isValid: false, error: 'Missing fields' };
     }
     if (!isValidEmail(formData.email)) {
       return { isValid: false, error: 'Invalid email' };
     }
     return { isValid: true };
   }
   
   function transformFormData(formData: FormData): AuthPayload {
     return {
       email: formData.email.toLowerCase(),
       password: hashPassword(formData.password),
       timestamp: Date.now()
     };
   }
   
   async function submitAuth(payload: AuthPayload): Promise<AuthResponse> {
     const response = await fetch('/api/auth', {
       method: 'POST',
       body: JSON.stringify(payload)
     });
     return response.json();
   }
   
   async function handleFormSubmit(formData: FormData) {
     const validation = validateFormData(formData);
     if (!validation.isValid) {
       setError(validation.error);
       return;
     }
     
     const payload = transformFormData(formData);
     const response = await submitAuth(payload);
     
     localStorage.setItem('token', response.token);
     router.push('/dashboard');
   }
   ```

2. **Keep functions small** (max 20-30 lines):
   - If a function is getting long, extract helper functions
   - Each function should do one thing well
   - Functions should be easy to test in isolation

### Hooks Usage

1. **Custom hooks** for shared logic:
   ```typescript
   // hooks/use-user.ts
   export function useUser(userId: string) {
     const [user, setUser] = useState<User | null>(null);
     const [loading, setLoading] = useState(true);
     const [error, setError] = useState<Error | null>(null);
     
     useEffect(() => {
       setLoading(true);
       fetchUser(userId)
         .then(setUser)
         .catch(setError)
         .finally(() => setLoading(false));
     }, [userId]);
     
     return { user, loading, error };
   }
   ```

2. **Hook ordering**:
   ```typescript
   function Component() {
     // 1. Router/navigation hooks
     const router = useRouter();
     
     // 2. Redux/Context hooks
     const { user } = useAuth();
     
     // 3. State hooks
     const [data, setData] = useState();
     
     // 4. Ref hooks
     const inputRef = useRef<HTMLInputElement>(null);
     
     // 5. Effect hooks
     useEffect(() => {}, []);
     
     // 6. Custom hooks
     const { items } = useItems();
     
     // 7. Callbacks and memos
     const handleClick = useCallback(() => {}, []);
     const computedValue = useMemo(() => {}, []);
   }
   ```

## Project Structure

### Directory Organization

```
app/                    # Next.js App Router
├── (auth)/            # Route groups
│   ├── login/
│   └── register/
├── dashboard/
│   ├── layout.tsx     # Dashboard layout
│   └── page.tsx       # Dashboard page
├── api/               # API routes
│   └── auth/
├── layout.tsx         # Root layout
└── page.tsx           # Home page

components/            # Shared components
├── ui/               # UI components
│   ├── button.tsx
│   └── input.tsx
├── forms/            # Form components
│   └── login-form.tsx
└── layouts/          # Layout components

lib/                  # Utilities and libraries
├── api.ts           # API client
├── utils.ts         # Utility functions
└── constants.ts     # Constants

hooks/               # Custom hooks
├── use-auth.ts
└── use-api.ts

types/               # TypeScript types
├── api.ts
└── user.ts

contexts/            # React contexts
└── auth-context.tsx

styles/              # Global styles
└── globals.css
```

### Import Organization

Order imports as follows:
```typescript
// 1. React/Next.js imports
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

// 2. Third-party imports
import { format } from 'date-fns';
import clsx from 'clsx';

// 3. Internal imports - absolute paths
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import type { User } from '@/types/user';

// 4. Relative imports
import { UserCard } from './user-card';
import styles from './styles.module.css';
```

## Component Standards

### Component Props

1. **Always define props interface**:
   ```typescript
   interface ButtonProps {
     variant?: 'primary' | 'secondary' | 'danger';
     size?: 'sm' | 'md' | 'lg';
     disabled?: boolean;
     onClick?: () => void;
     children: React.ReactNode;
   }
   
   export function Button({
     variant = 'primary',
     size = 'md',
     disabled = false,
     onClick,
     children
   }: ButtonProps) {
     // Component implementation
   }
   ```

2. **Use proper prop spreading**:
   ```typescript
   interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
     label?: string;
     error?: string;
   }
   
   export function Input({ label, error, ...inputProps }: InputProps) {
     return (
       <div>
         {label && <label>{label}</label>}
         <input {...inputProps} />
         {error && <span className="error">{error}</span>}
       </div>
     );
   }
   ```

### Component Composition

1. **Use composition over inheritance**:
   ```typescript
   // Good - Composition
   function Card({ children, className }: CardProps) {
     return (
       <div className={clsx('card', className)}>
         {children}
       </div>
     );
   }
   
   function UserCard({ user }: UserCardProps) {
     return (
       <Card className="user-card">
         <h3>{user.name}</h3>
         <p>{user.email}</p>
       </Card>
     );
   }
   ```

2. **Extract reusable logic into hooks**:
   ```typescript
   // Good
   function UserList() {
     const { users, loading, error } = useUsers();
     
     if (loading) return <Loading />;
     if (error) return <Error error={error} />;
     
     return <UserGrid users={users} />;
   }
   ```

## State Management

### Local State

Use local state for component-specific data:
```typescript
function SearchBar() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  const handleSearch = (value: string) => {
    setQuery(value);
    // Fetch suggestions
  };
  
  return (
    <input
      value={query}
      onChange={(e) => handleSearch(e.target.value)}
    />
  );
}
```

### Context API

Use Context for cross-component state:
```typescript
// contexts/theme-context.tsx
interface ThemeContextType {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };
  
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### Form State

Use controlled components with proper validation:
```typescript
function LoginForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      // Submit form
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
    </form>
  );
}
```

## Styling Standards

### Tailwind CSS Usage

1. **Use Tailwind utilities first**:
   ```typescript
   // Good
   <div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-md">
     <h2 className="text-xl font-semibold text-gray-800">Title</h2>
   </div>
   
   // Avoid inline styles unless necessary
   <div style={{ display: 'flex' }}> // Bad
   ```

2. **Create component variants with clsx**:
   ```typescript
   import clsx from 'clsx';
   
   interface ButtonProps {
     variant?: 'primary' | 'secondary';
     size?: 'sm' | 'md' | 'lg';
   }
   
   export function Button({ variant = 'primary', size = 'md', className, ...props }: ButtonProps) {
     return (
       <button
         className={clsx(
           'font-medium rounded-md transition-colors',
           {
             // Variants
             'bg-blue-600 text-white hover:bg-blue-700': variant === 'primary',
             'bg-gray-200 text-gray-800 hover:bg-gray-300': variant === 'secondary',
             
             // Sizes
             'px-3 py-1.5 text-sm': size === 'sm',
             'px-4 py-2': size === 'md',
             'px-6 py-3 text-lg': size === 'lg',
           },
           className
         )}
         {...props}
       />
     );
   }
   ```

3. **Responsive design**:
   ```typescript
   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
     {/* Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns */}
   </div>
   ```

### CSS Modules (when needed)

For complex component-specific styles:
```css
/* user-card.module.css */
.card {
  @apply bg-white rounded-lg shadow-md p-4;
}

.card:hover {
  @apply shadow-lg transform -translate-y-1;
}

@media (prefers-color-scheme: dark) {
  .card {
    @apply bg-gray-800;
  }
}
```

## API Integration

### API Client Setup

```typescript
// lib/api-client.ts
class ApiClient {
  private baseURL: string;
  private headers: Record<string, string>;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || '';
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: any
  ): Promise<T> {
    const config: RequestInit = {
      method,
      headers: this.headers,
      credentials: 'include',
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>('GET', endpoint);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>('POST', endpoint, data);
  }

  // Other methods...
}

export const apiClient = new ApiClient();
```

### Data Fetching Hooks

```typescript
// hooks/use-api.ts
export function useApi<T>(endpoint: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await apiClient.get<T>(endpoint);
        setData(result);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [endpoint]);

  return { data, loading, error };
}
```

### Error Handling

```typescript
// components/error-boundary.tsx
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<
  { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    
    // Send to Sentry
    import * as Sentry from '@sentry/nextjs';
    Sentry.withScope((scope) => {
      scope.setExtras(errorInfo);
      scope.setLevel('error');
      Sentry.captureException(error);
    });
  }

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallback || DefaultErrorFallback;
      return <Fallback error={this.state.error!} />;
    }

    return this.props.children;
  }
}
```

### Sentry Error Monitoring

1. **Initialize Sentry** (already configured in `sentry.*.config.ts`):
   ```typescript
   // sentry.client.config.ts
   import * as Sentry from "@sentry/nextjs";
   
   Sentry.init({
     dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
     environment: process.env.NODE_ENV,
     integrations: [
       new Sentry.BrowserTracing(),
       new Sentry.Replay()
     ],
     tracesSampleRate: 0.1,
     replaysSessionSampleRate: 0.1,
     replaysOnErrorSampleRate: 1.0,
   });
   ```

2. **Capture errors with context**:
   ```typescript
   import * as Sentry from '@sentry/nextjs';
   
   try {
     await riskyOperation();
   } catch (error) {
     Sentry.captureException(error, {
       tags: {
         component: 'PaymentForm',
         action: 'submit'
       },
       extra: {
         orderId: order.id,
         amount: order.total,
         currency: order.currency
       }
     });
     
     // Still handle the error for UX
     setError('Payment failed. Please try again.');
   }
   ```

3. **Set user context**:
   ```typescript
   // After successful authentication
   Sentry.setUser({
     id: user.id,
     email: user.email,
     username: user.username,
   });
   
   // On logout
   Sentry.setUser(null);
   ```

4. **Add breadcrumbs for user actions**:
   ```typescript
   Sentry.addBreadcrumb({
     message: 'User searched for product',
     category: 'user-action',
     level: 'info',
     data: {
       searchTerm: query,
       resultsCount: results.length,
       timestamp: Date.now()
     }
   });
   ```

5. **Performance monitoring**:
   ```typescript
   const transaction = Sentry.startTransaction({
     op: 'page.load',
     name: 'Dashboard'
   });
   
   try {
     const span = transaction.startChild({
       op: 'api.fetch',
       description: 'Load dashboard data'
     });
     
     const data = await fetchDashboardData();
     span.finish();
     
     setDashboardData(data);
   } finally {
     transaction.finish();
   }
   ```

6. **API route error handling**:
   ```typescript
   // app/api/[...]/route.ts
   export async function POST(request: NextRequest) {
     try {
       const data = await processRequest(request);
       return NextResponse.json(data);
     } catch (error) {
       Sentry.captureException(error, {
         tags: { api_route: 'user_update' },
         extra: { 
           method: request.method,
           url: request.url 
         }
       });
       
       return NextResponse.json(
         { error: 'Internal Server Error' },
         { status: 500 }
       );
     }
   }
   ```

7. **Privacy considerations**:
   ```typescript
   // NEVER send sensitive data to Sentry
   // BAD
   Sentry.captureException(error, {
     extra: {
       password: userPassword,      // NEVER
       creditCard: cardNumber,      // NEVER
       socialSecurity: ssn,         // NEVER
       apiKey: secretKey           // NEVER
     }
   });
   
   // GOOD
   Sentry.captureException(error, {
     extra: {
       userId: user.id,
       cardLast4: cardNumber.slice(-4),
       transactionType: 'purchase'
     }
   });
   ```

## Testing Standards

### Component Testing

```typescript
// __tests__/components/button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies correct variant classes', () => {
    const { rerender } = render(<Button variant="primary">Button</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-blue-600');
    
    rerender(<Button variant="secondary">Button</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-gray-200');
  });
});
```

### Hook Testing

```typescript
// __tests__/hooks/use-api.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useApi } from '@/hooks/use-api';

// Mock the API client
jest.mock('@/lib/api-client');

describe('useApi', () => {
  it('fetches data successfully', async () => {
    const mockData = { id: 1, name: 'Test' };
    (apiClient.get as jest.Mock).mockResolvedValue(mockData);

    const { result } = renderHook(() => useApi('/test'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.data).toEqual(mockData);
      expect(result.current.error).toBeNull();
    });
  });
});
```

## Performance Guidelines

### Code Splitting

```typescript
// Lazy load components
const DashboardAnalytics = lazy(() => import('./dashboard-analytics'));

function Dashboard() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <DashboardAnalytics />
    </Suspense>
  );
}
```

### Memoization

```typescript
// Memoize expensive computations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);

// Memoize components
const MemoizedComponent = memo(ExpensiveComponent);
```

### Image Optimization

```typescript
import Image from 'next/image';

// Use Next.js Image component
<Image
  src="/hero.jpg"
  alt="Hero image"
  width={1200}
  height={600}
  priority // For above-the-fold images
  placeholder="blur"
  blurDataURL={blurDataUrl}
/>
```

### Bundle Size Optimization

```typescript
// Import only what you need
import { format } from 'date-fns/format'; // Good
import * as dateFns from 'date-fns'; // Bad

// Use dynamic imports for large libraries
const Chart = dynamic(() => import('react-chartjs-2'), {
  ssr: false,
  loading: () => <ChartSkeleton />
});
```

### Performance Monitoring with Sentry

1. **Monitor page load performance**:
   ```typescript
   // In page components
   useEffect(() => {
     const transaction = Sentry.startTransaction({
       op: 'navigation',
       name: `Page: ${pageName}`,
     });
     
     // Set transaction on scope so all events are tied to it
     Sentry.getCurrentHub().configureScope(scope => scope.setSpan(transaction));
     
     return () => {
       transaction.finish();
     };
   }, []);
   ```

2. **Monitor API calls**:
   ```typescript
   async function fetchData(endpoint: string) {
     const span = Sentry.getCurrentHub()
       .getScope()
       ?.getSpan()
       ?.startChild({
         op: 'http.client',
         description: `GET ${endpoint}`,
       });
     
     try {
       const response = await fetch(endpoint);
       span?.setStatus('ok');
       return response.json();
     } catch (error) {
       span?.setStatus('internal_error');
       throw error;
     } finally {
       span?.finish();
     }
   }
   ```

3. **Monitor component render performance**:
   ```typescript
   import { Profiler } from 'react';
   
   function onRenderCallback(
     id: string,
     phase: 'mount' | 'update',
     actualDuration: number,
   ) {
     if (actualDuration > 16) { // Longer than one frame
       Sentry.captureMessage(`Slow render: ${id}`, 'warning', {
         tags: { component: id, phase },
         extra: { duration: actualDuration }
       });
     }
   }
   
   <Profiler id="ExpensiveComponent" onRender={onRenderCallback}>
     <ExpensiveComponent />
   </Profiler>
   ```

## Accessibility Standards

### ARIA Labels

```typescript
<button
  aria-label="Close dialog"
  onClick={onClose}
>
  <XIcon aria-hidden="true" />
</button>

<input
  aria-label="Search products"
  aria-describedby="search-error"
  aria-invalid={!!error}
/>
{error && <span id="search-error">{error}</span>}
```

### Keyboard Navigation

```typescript
function Dialog({ isOpen, onClose, children }: DialogProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      {children}
    </div>
  );
}
```

### Focus Management

```typescript
function Modal({ isOpen, onClose, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      modalRef.current?.focus();
    } else {
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  return (
    <div ref={modalRef} tabIndex={-1}>
      {children}
    </div>
  );
}
```

## Code Review Checklist

Before submitting code for review, ensure:

- [ ] TypeScript strict mode passes without errors
- [ ] Components follow naming conventions
- [ ] Components follow Single Responsibility Principle
- [ ] Everything that can be a component is a component
- [ ] No component exceeds 150 lines
- [ ] No file exceeds 500 lines (prefer 300)
- [ ] Functions are small and focused (max 30 lines)
- [ ] Props interfaces are defined
- [ ] No `any` types (use `unknown` if necessary)
- [ ] Proper error handling in place
- [ ] Loading and error states handled
- [ ] Error boundaries implemented for critical sections
- [ ] Sentry error capture added for try-catch blocks
- [ ] User context set for Sentry after authentication
- [ ] No sensitive data sent to Sentry
- [ ] Performance monitoring added for slow operations
- [ ] Accessibility attributes included
- [ ] Responsive design implemented
- [ ] Code is properly formatted (Prettier)
- [ ] ESLint rules pass
- [ ] Tests written and passing
- [ ] No console.log statements
- [ ] Performance optimizations applied where needed
- [ ] Bundle size impact considered