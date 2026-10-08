-- Database and user for the demo application.
-- Run as the postgres superuser:  sudo -u postgres psql -f create-databases.sql
--
-- The password is NOT set here. Set it interactively afterwards so it never
-- ends up in files or in the shell history:
--   \password app_user

CREATE USER app_user;
CREATE DATABASE app_db OWNER app_user;
REVOKE CONNECT ON DATABASE app_db FROM PUBLIC;
