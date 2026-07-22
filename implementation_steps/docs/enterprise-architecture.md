# Capsule Enterprise Architecture: One-Click Setup & Multi-Tenancy

This document explains exactly how we will upgrade Capsule from a single-user tool to an enterprise-grade platform. It is broken down into simple concepts and their precise technical implementations.

## 1. The "One-Click" Setup (GitHub App Integration)

**The Problem:** Right now, users have to manually create Personal Access Tokens (PATs) and set up webhook URLs in their repository settings. It is tedious and error-prone.

**Simple Explanation:** 
Instead of making users manually connect wires, we will turn Capsule into an official "GitHub App". Just like installing an app on your phone, a user clicks "Install Capsule", selects which repositories it can access, and GitHub handles all the wiring automatically in the background.

**Technical Implementation:**
- **App Registration:** You will register Capsule as a GitHub App and generate a `.pem` Private Key and an `App ID`.
- **Webhooks:** When the app is installed, GitHub sends a `installation` webhook to Capsule containing an `installation_id`. We save this ID in our database.
- **Dynamic Authentication:** We will delete the static `GITHUB_TOKEN` from our `.env` file. Instead, whenever Capsule needs to comment on a PR, it will:
  1. Use the App's `.pem` Private Key to sign a JSON Web Token (JWT).
  2. Send that JWT to GitHub to request a temporary, 1-hour "Installation Access Token" specifically for that repository.
  3. Use that temporary token to post the PR comment.
- **Files Modified:** We will create `backend/services/github_app.py` to handle the cryptographic signing and token exchange.

---

## 2. Preventing Horizontal Data Leaks (Multi-Tenancy)

**The Problem:** If all leads across a company use the same backend, we must guarantee that "Team Alpha" cannot read the PR summaries or Business Requirements (BRD) of "Team Beta".

**Simple Explanation:**
We need to build "apartments" inside our database. Right now, Capsule is a single house where everyone shares the same living room. We will convert it into an apartment building where every team gets their own locked door, and the system physically prevents someone from entering the wrong apartment.

**Technical Implementation (Tenant Isolation):**
- **Tenant ID Injection:** We will introduce the concept of a `tenant_id` (representing a specific team or project). 
- **Database Schema Upgrades:** Every single data table (like `pr_analyses`, `changelog_entries`, `brd_versions`) will be updated to include a `tenant_id` column.
- **Application-Level Filtering:** We will update `backend/database.py`. Every SQL query (e.g., `SELECT * FROM pr_analyses`) will be strictly modified to *always* append `WHERE tenant_id = ?`. 
- **The Guarantee:** Even if a user tries to access `/api/pr/123`, the database will return `404 Not Found` if PR 123 belongs to a `tenant_id` they do not have access to.

---

## 3. User Authentication & Roles (Admin vs. Lead)

**The Problem:** Currently, the Chrome Extension logs in using a single, shared `API_KEY`. If everyone uses the same key, we don't know *who* is making a request, and we can't restrict what they can do.

**Simple Explanation:**
We will throw away the shared key and issue digital "ID Badges" (JWTs) when users log in. 
- An **Admin ID Badge** allows the user to edit the Business Requirements (BRD) and add new repositories.
- A **Lead ID Badge** allows the user to view PR summaries and trigger analyses, but they cannot change the core rules.

**Technical Implementation (JWT & RBAC):**
- **OAuth Login:** Users will log in via GitHub OAuth.
- **Issuing JWTs:** Upon successful login, the backend will generate a JSON Web Token (JWT). This token securely encodes payload data like:
  ```json
  {
    "user_id": 42,
    "role": "lead",
    "allowed_tenant_ids": [5, 9]
  }
  ```
- **Middleware Security:** We will update `backend/middleware/security.py`. Instead of checking `if request_header == API_KEY`, it will verify the cryptographic signature of the JWT.
- **Role-Based Access Control (RBAC):** We will use FastAPI dependencies (e.g., `Depends(require_admin)`) on sensitive endpoints like `POST /api/brd`. This dependency will read the JWT, check if `"role" == "admin"`, and throw a `403 Forbidden` error if it is not.

---

## 4. Cross-Device Accessibility (Web Dashboard)

**The Problem:** You need to check Capsule on other devices (like a mobile phone or a different laptop) using your GitHub login, but Chrome Extensions only work on desktop browsers. Furthermore, if your backend is only running on your local computer, other devices can't reach it.

**Simple Explanation:**
To make Capsule "always running" and accessible from anywhere, we do two things:
1. **Host the Backend Online:** By deploying the backend to a cloud provider (like Render, DigitalOcean, or AWS), it runs 24/7. Your extension on *any* laptop can now connect to it.
2. **Build a Web Dashboard:** Since you can't install Chrome Extensions on mobile devices like iPhones or iPads, we will build a standalone Web Dashboard. This is a website (e.g., `capsule.yourcompany.com`) where you can simply log in with GitHub on any device and view your entire CI/CD dashboard, PR summaries, and BRD settings exactly as you would on the extension.

**Technical Implementation:**
- We will add a frontend interface directly served by FastAPI (or a standalone React/Vite app).
- This dashboard will consume the exact same protected JWT APIs as the Chrome Extension.
- The Chrome Extension will remain useful for *injecting* UI directly into GitHub.com while you are on a desktop, but the Web Dashboard becomes your central command center for cross-device management.

---

## Summary of Database Changes

To support the above, `backend/database.py` will be migrated to this new schema:

1. **`users` Table:** Tracks actual humans.
   - `id`, `github_username`, `global_role`
2. **`tenants` (or `teams`) Table:** Tracks isolated workspaces.
   - `id`, `name`, `changelog_repo`
3. **`user_tenant_access` Table:** The mapping table that decides who can enter which apartment.
   - `user_id`, `tenant_id`, `tenant_role` (admin vs viewer)
4. **`github_installations` Table:** Links a GitHub App installation to a specific tenant workspace.
   - `installation_id`, `tenant_id`
