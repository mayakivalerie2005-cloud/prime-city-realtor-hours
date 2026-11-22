# PRIME CITY REAL ESTATE — Agent Management & Payroll

Private role-based dashboard with administrator controls and individual agent logins. Agents can see only their own sales, weekly 15% commission estimate, and archived payroll statements. The administrator manages agents and sales and sees business-wide totals.

## Included
- `index.html` — sign-in and role-aware dashboard
- `schema.sql` — Supabase tables and row-level security (RLS)
- `scripts/weekly-payroll.mjs` — weekly payroll calculation and Discord delivery
- `.github/workflows/weekly-agent-payroll.yml` — Sunday 20:00 WAT schedule (19:00 UTC)

## 1. Create and configure Supabase
1. Create a Supabase project.
2. In **Authentication → Settings**, disable public sign-ups.
3. In **SQL Editor**, run all of `schema.sql`.
4. In **Authentication → Users**, create your administrator user.
5. Copy that user's UUID. In SQL Editor, add the admin profile (replace the UUID):

```sql
insert into public.profiles (user_id, role, agent_id)
values ('ADMIN-AUTH-USER-UUID', 'admin', null);
```

6. Copy the project URL and anon/public key from **Project Settings → API**.

## 2. Configure the dashboard
Open `index.html` and replace:
- `YOUR_SUPABASE_PROJECT_URL` with your Supabase project URL
- `YOUR_SUPABASE_ANON_KEY` with your Supabase anon/public key

The anon key is designed for browser use. RLS policies enforce role-based access. **Never put the service-role key in the dashboard or commit it to GitHub.**

## 3. Add agent accounts (repeat for every agent)
1. Sign in to the dashboard as admin and add the agent under **Agents**. Note the agent record UUID; the easiest way to find it is Supabase **Table Editor → agents**.
2. In Supabase **Authentication → Users**, create/invite a user for the agent's email. Use the email address the agent will sign in with.
3. Copy the new Auth user's UUID and the matching agent row UUID.
4. In SQL Editor, run this mapping (replace both UUIDs):

```sql
insert into public.profiles (user_id, role, agent_id)
values ('AGENT-AUTH-USER-UUID', 'agent', 'AGENT-ROW-UUID');
```

5. Send the agent their invite/password setup instructions. They sign in at the same dashboard URL using their own email and password.

**Important:** Each agent profile must map to exactly one agent record. Do not give agents the admin role. Agents are read-only: they cannot add, edit, confirm, or delete sales or see another agent's sales or commission.

## 4. Add the GitHub workflow
Copy `index.html`, `schema.sql`, `scripts/weekly-payroll.mjs`, and `.github/workflows/weekly-agent-payroll.yml` into the root of your existing `PRIME-CITY-REALTOR-HOURS` repository. Keep your existing business-hours workflow files unchanged.

In GitHub, open **Settings → Secrets and variables → Actions** and add:
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service-role key (GitHub Actions secret only)
- `DISCORD_WEBHOOK_URL` — your Discord webhook URL

Do not commit secret values to the repository.

## 5. Publish the dashboard
Publish the repository root (or put `index.html` in your configured GitHub Pages source). Use HTTPS only. Both admin and agents use the same sign-in page; the dashboard automatically shows the correct role-specific view.

## 6. Payroll rules
- Currency: **USD ($)**.
- Commission: **15%** of confirmed `sold` property value.
- Pending sales are excluded.
- Weekly period: Monday through Sunday in WAT (`Africa/Lagos`).
- Payroll report: Sunday at 20:00 WAT.
- GitHub Actions cron: `0 19 * * 0` (19:00 UTC; WAT is UTC+1).
- The Discord report contains company-wide totals and each agent's commission.
- Each agent's own archived weekly statement is saved in `payroll_agent_rows` and is visible only to that agent and the service-role payroll job.
- The dashboard calculates amounts owed; it does not transfer money.

## Security notes
- Keep public sign-ups disabled.
- Use strong, unique passwords and HTTPS.
- Keep the Supabase service-role key only in GitHub Actions secrets.
- RLS policies prevent agents from accessing other agents' records. Test with one admin account and one agent account before entering live payroll data.
- Back up the Supabase project regularly.
