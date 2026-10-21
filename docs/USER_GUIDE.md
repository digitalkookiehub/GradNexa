# User guide

The guide lives inside the application so it can be access-controlled: sign in as an **Admin** and open **User guide** in the top menu (`/guide`). A left sidebar lists every section and procedure; each procedure is a numbered, click-by-click list of steps.

- **Step-by-step procedures:** `backend/app/content/guide.json`
- **Written guide (full text):** `backend/app/content/user_guide.md`
- Served by `GET /api/v1/guide`; who may read it is `GUIDE_ROLES` in `backend/app/services/guide_service.py` (ADMIN only for now).

Edit the files and restart/redeploy the backend. Tests check that every page path in the guide is a real frontend route and that every link between procedures resolves. Button and field names in the steps were taken from the application's screens; re-check them after any UI change.
