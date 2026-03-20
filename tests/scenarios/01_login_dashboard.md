# 01. Login & Dashboard Scenario

## Objective
Verify that the login page correctly redirects to the dashboard and that the user's dashboard displays correctly.

## Pre-conditions
- The web server is running and serving `/output`.
- There is a mock user or we can use the UI to navigate.
- If we do not have a working Supabase instance for tests, verify the UI elements independently of full auth flow.

## Steps
1. Navigate to `/login.html`.
2. Observe the "로그인" (Login) card and "Google로 계속하기" buttons.
3. Observe the email input fields.
4. Click on the "홈으로" (Back to Home) or "둘러보기" (Browse) link to directly navigate to the dashboard without authenticating.
5. On `/index.html` (Dashboard), verify the presence of the header "Master Valuation Dashboard".
6. Verify that the table renders correctly (check for `#masterTable`).
7. Wait playfully to confirm no errors appear.

## Expected Results
- The login page should render without broken CSS.
- The dashboard should render without crashing or empty screens.
