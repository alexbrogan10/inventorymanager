# Frontend

React + TypeScript SPA for the AI Inventory Management System, built with
Vite and Material UI. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
for the folder structure and state-management decisions this code follows.

## Local development

```bash
npm install
cp .env.example .env   # then edit VITE_API_BASE_URL if the backend isn't on localhost:8000
npm run dev
```

App runs at http://localhost:5173 and expects the backend API described in
[`../backend/README.md`](../backend/README.md) to be reachable.

## Testing

```bash
npm run test            # run once
npm run test:watch      # watch mode
npm run test:coverage    # with coverage report
```

Tests are colocated with the components/modules they cover
(`Component.test.tsx` next to `Component.tsx`).

## Linting & formatting

```bash
npm run lint          # oxlint
npm run format:check   # prettier --check
npm run format          # prettier --write
```

## Building for production

```bash
npm run build   # type-checks (tsc -b) then builds to dist/
npm run preview  # serve the production build locally
```
