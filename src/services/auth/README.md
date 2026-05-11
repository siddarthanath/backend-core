Thin wrapper around the Supabase Admin SDK for server-side auth operations.

Handles user deletion, email updates, and password resets. Does not manage JWT tokens — token creation and verification happen on the frontend (Supabase) and in `core/dependencies/auth.py` respectively.
