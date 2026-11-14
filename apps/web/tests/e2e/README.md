# End-to-end tests (Playwright)

Five specs: onboarding, approve, reject-with-reason, edit-then-approve, degraded-mode banner.
`playwright.config.ts` starts the backend (offline model profile, fresh state dir, `.venv` uvicorn on :8000) and `next dev` on :3000.

```
cd apps/web && npm install && npx playwright install chromium
npm run test:e2e            # writes apps/web/playwright-report/ (HTML); open with: npx playwright show-report
```
Each test registers a fresh user, so tests are isolated. The report folder is git-ignored; regenerate it with the command above.


**Windows:** the default config uses POSIX paths; run `npx playwright test -c playwright.win.config.ts` instead. Last run: 5 passed (1.5 min); the HTML report is committed at `docs/playwright-report/index.html` (download the folder and open `index.html`).
