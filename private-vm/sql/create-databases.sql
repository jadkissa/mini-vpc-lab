-- One database and one user per service (database per service).
-- Run as the postgres superuser:  sudo -u postgres psql -f create-databases.sql
--
-- Passwords are NOT set here. Set them interactively afterwards so they never
-- end up in files or in the shell history:
--   \password product_user
--   \password order_user

CREATE USER product_user;
CREATE DATABASE product_db OWNER product_user;
REVOKE CONNECT ON DATABASE product_db FROM PUBLIC;

CREATE USER order_user;
CREATE DATABASE order_db OWNER order_user;
REVOKE CONNECT ON DATABASE order_db FROM PUBLIC;
