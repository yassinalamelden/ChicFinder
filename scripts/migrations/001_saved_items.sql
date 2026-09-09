-- 001_saved_items.sql
-- Saved items (wishlist) for the ChicFinder mobile app.
--
-- Keyed by the Firebase uid so no separate users table is needed. The uid is
-- the only user-identifying column stored, which keeps the App Store privacy
-- disclosure minimal and makes account deletion a single DELETE.
--
-- Apply with:
--   psql "$DATABASE_URL" -f scripts/migrations/001_saved_items.sql

CREATE TABLE IF NOT EXISTS saved_items (
    uid         TEXT        NOT NULL,
    item_id     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (uid, item_id)
);

-- The hot query is "everything this user saved, newest first".
CREATE INDEX IF NOT EXISTS saved_items_uid_created_idx
    ON saved_items (uid, created_at DESC);
