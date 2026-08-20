# n8n Marketing Automation Workflows

This directory contains automation blueprints and exported workflow JSON templates for the **Marathon Registration & Marketing Automation Platform**.

## Planned Workflows (Phase 4):
1. `marathon_post_registration.json`: Triggered on `REGISTRATION_CONFIRMED` event. Sends multi-channel alerts and syncs participant logs.
2. `marathon_drip_reminders.json`: Scheduled drip sequences:
   - **T-30 Days**: Training schedule & hydration guide
   - **T-7 Days**: Expo bib collection venue & slot details
   - **T-1 Day**: Race day flag-off & parking guide
3. `marathon_post_race.json`:
   - **T+1 Day**: Finisher certificate & photo gallery link
