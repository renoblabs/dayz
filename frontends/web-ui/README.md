# DayZ HiveAPI - Web UI

Modern React/TypeScript admin dashboard for the DayZ HiveAPI.

## Features

- 📊 **Real-time Dashboard** - Live stats and metrics
- 🔴 **Event Streaming** - Server-Sent Events for real-time updates
- 📋 **Event History** - Browse and filter all system events
- 👥 **Character Management** - View and manage player characters
- 🎨 **Modern UI** - Built with React, TypeScript, and TailwindCSS

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Running HiveAPI backend (http://localhost:8000)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will be available at http://localhost:3000

### Building for Production

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Styling
- **React Router** - Routing
- **Axios** - HTTP client
- **Lucide React** - Icons
- **date-fns** - Date formatting

## API Integration

The UI connects to the HiveAPI backend via proxy configuration in `vite.config.ts`. All requests to `/v1/*` are proxied to `http://localhost:8000`.

## Development

- Edit pages in `src/pages/`
- Add components in `src/components/`
- API calls are in `src/api/client.ts`
- Custom hooks in `src/hooks/`
