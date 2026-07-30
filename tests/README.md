# End-to-End Tests

Cross-service tests that exercise the deployed stack (frontend + backend +
database together), distinct from the unit/integration tests that live next
to the code they test (`backend/tests/`, and colocated `*.test.tsx` files in
`frontend/src/`). See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#6-testing-strategy)
for the reasoning.

Empty until a later milestone introduces e2e coverage.
