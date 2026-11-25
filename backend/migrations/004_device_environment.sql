ALTER TABLE devices ADD COLUMN environment TEXT CHECK(environment IN ('sandbox','production'));
