ALTER TABLE devices ADD COLUMN kind TEXT NOT NULL DEFAULT 'alert' CHECK(kind IN ('alert','voip'));
