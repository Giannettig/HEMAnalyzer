-- docker-compose exec db psql -U hema_user -d hema_ratings
-- docker compose build --no-cache && docker compose up


-- Drop existing tables if they exist
DROP TABLE IF EXISTS fights CASCADE;
DROP TABLE IF EXISTS fighters CASCADE;
DROP TABLE IF EXISTS tournaments CASCADE;
DROP TABLE IF EXISTS achievements CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS clubs CASCADE;
DROP TABLE IF EXISTS countries CASCADE;
DROP TABLE IF EXISTS rankings CASCADE;
DROP TABLE IF EXISTS match_results CASCADE;

-- Create tables
CREATE TABLE countries (
    country_id INTEGER PRIMARY KEY,
    country_name VARCHAR(100),
    region VARCHAR(100),
    sub_region VARCHAR(100),
    population INTEGER,
    community INTEGER,
    community_label VARCHAR(100),
    country_code VARCHAR(100)
);

CREATE TABLE clubs (
    club_id INTEGER PRIMARY KEY,
    club_name VARCHAR(200),
    club_country VARCHAR(100),
    club_state VARCHAR(100),
    club_city VARCHAR(100),
    club_members INTEGER,
    club_parent_id INTEGER,
    club_url VARCHAR(200),
    FOREIGN KEY (club_parent_id) REFERENCES clubs(club_id)
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    event_brand VARCHAR(100),
    event_year INTEGER,
    event_name VARCHAR(200),
    event_date DATE,
    event_country VARCHAR(100),
    event_city VARCHAR(100),
    event_url VARCHAR(200)
);

CREATE TABLE tournaments (
    tournament_id INTEGER PRIMARY KEY,
    tournament_name VARCHAR(200),
    event_id INTEGER,
    tournament_category VARCHAR(50),
    tournament_weapon VARCHAR(100),
    tournament_note VARCHAR(100),
    match_count INTEGER,
    fighter_count INTEGER,
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

CREATE TABLE fighters (
    fighter_id INTEGER PRIMARY KEY,
    fighter_name VARCHAR(200),
    fighter_nationality VARCHAR(100),
    fighter_club_id INTEGER,
    fighter_club_name VARCHAR(200),
    fighter_url VARCHAR(200),
    rank_longsword INTEGER,
    weighted_rating_longsword DECIMAL(10,2),
    FOREIGN KEY (fighter_club_id) REFERENCES clubs(club_id)
);

CREATE TABLE achievements (
    fighter_id INTEGER,
    tier_id INTEGER,
    achieved BOOLEAN,
    percentile DECIMAL,
    achievement_tier VARCHAR(50),
    achievement_name VARCHAR(200),
    achievement_description VARCHAR(200),
    achievement_icon VARCHAR(200),
    FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
);

CREATE TABLE fights (
    match_id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    event_name VARCHAR(200),
    tournament_name VARCHAR(200),
    tournament_category VARCHAR(50),
    tournament_note VARCHAR(100),
    tournament_weapon VARCHAR(100),
    fighter_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    fighter_1 VARCHAR(200),
    fighter_2 VARCHAR(200),
    fighter_1_result VARCHAR(50),
    fighter_2_result VARCHAR(50),
    stage VARCHAR(150), -- Increased length to avoid value truncation
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
    FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id),
    FOREIGN KEY (opponent_id) REFERENCES fighters(fighter_id)
);

CREATE TABLE rankings (
    ranking_id SERIAL PRIMARY KEY,
    rank INTEGER,
    fighter_id INTEGER NOT NULL,
    fighter_name VARCHAR(100),
    category VARCHAR(100),
    month VARCHAR(20),
    weighted_rating FLOAT,
    club VARCHAR(200),
    month_date DATE
);

CREATE TABLE match_results (
    match_id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    event_name VARCHAR(200),
    tournament_name VARCHAR(200),
    tournament_category VARCHAR(50),
    tournament_note VARCHAR(100),
    tournament_weapon VARCHAR(100),
    fighter_id INTEGER NOT NULL,
    is_final BOOLEAN,
    club_id INTEGER,
    opponent_id INTEGER NOT NULL,
    fighter_name VARCHAR(200),
    opponent_name VARCHAR(200),
    result VARCHAR(50),
    stage VARCHAR(150), -- Increased length to avoid value truncation
    debut_fight BOOLEAN,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
    FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id),
    FOREIGN KEY (opponent_id) REFERENCES fighters(fighter_id)
);

-- Begin transaction
BEGIN;

-- Temporarily defer all constraints
SET CONSTRAINTS ALL DEFERRED;

-- Load data in correct order
\copy countries(country_id, country_name, region, sub_region, population, community, community_label,country_code) FROM '/data/hema_countries.csv' WITH (FORMAT csv, HEADER true);

\copy clubs(club_id, club_name, club_country, club_state, club_city, club_members, club_parent_id, club_url) FROM '/data/hema_clubs.csv' WITH (FORMAT csv, HEADER true);

\copy events(event_id, event_brand, event_year, event_name, event_date, event_country, event_city, event_url) FROM '/data/hema_events.csv' WITH (FORMAT csv, HEADER true);

\copy tournaments(tournament_id, tournament_name, event_id, tournament_category, tournament_weapon, tournament_note, match_count, fighter_count) FROM '/data/hema_tournaments.csv' WITH (FORMAT csv, HEADER true);

-- Add dummy fighter with fighter_id = 0 for anonymous entries
INSERT INTO fighters (fighter_id, fighter_name, fighter_nationality, fighter_club_id, fighter_club_name, fighter_url, rank_longsword, weighted_rating_longsword)
VALUES (0, 'Anonymous Fighter', NULL, NULL, NULL, NULL, NULL, NULL);

\copy fighters FROM '/data/hema_fighters.csv' WITH (FORMAT csv, HEADER true);

-- Then create and load achievements
CREATE TEMP TABLE temp_achievements (LIKE achievements);
\copy temp_achievements FROM '/data/hema_achievements.csv' WITH (FORMAT csv, HEADER true);
INSERT INTO achievements 
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM fighters WHERE fighters.fighter_id = temp_achievements.fighter_id
        ) THEN temp_achievements.fighter_id 
        ELSE 0 
    END as fighter_id,
    tier_id,
    achieved,
    percentile,
    achievement_tier,
    achievement_name,
    achievement_description,
    achievement_icon
FROM temp_achievements;
DROP TABLE temp_achievements;

-- Create temporary fights table and load data
CREATE TEMP TABLE temp_fights (LIKE fights);
\copy temp_fights FROM '/data/hema_fights.csv' WITH (FORMAT csv, HEADER true);
INSERT INTO fights 
SELECT 
    match_id,
    tournament_id,
    event_id,
    event_name,
    tournament_name,
    tournament_category,
    tournament_note,
    tournament_weapon,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM fighters WHERE fighters.fighter_id = temp_fights.fighter_id
        ) THEN temp_fights.fighter_id 
        ELSE 0 
    END as fighter_id,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM fighters WHERE fighters.fighter_id = temp_fights.opponent_id
        ) THEN temp_fights.opponent_id 
        ELSE 0 
    END as opponent_id,
    fighter_1,
    fighter_2,
    fighter_1_result,
    fighter_2_result,
    stage
FROM temp_fights;
DROP TABLE temp_fights;

\copy rankings(rank, fighter_id, fighter_name, category, month, weighted_rating, club, month_date) FROM '/data/hema_rankings.csv' WITH (FORMAT csv, HEADER true);

-- Create temporary match_results table and load data
CREATE TEMP TABLE temp_match_results (LIKE match_results);
\copy temp_match_results FROM '/data/hema_match_results.csv' WITH (FORMAT csv, HEADER true);
INSERT INTO match_results 
SELECT 
    match_id,
    tournament_id,
    event_id,
    event_name,
    tournament_name,
    tournament_category,
    tournament_note,
    tournament_weapon,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM fighters WHERE fighters.fighter_id = temp_match_results.fighter_id
        ) THEN temp_match_results.fighter_id 
        ELSE 0 
    END as fighter_id,
    is_final,
    club_id,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM fighters WHERE fighters.fighter_id = temp_match_results.opponent_id
        ) THEN temp_match_results.opponent_id 
        ELSE 0 
    END as opponent_id,
    fighter_name,
    opponent_name,
    result,
    stage,
    debut_fight
FROM temp_match_results;
DROP TABLE temp_match_results;

-- Commit transaction
COMMIT;


-- Create indexes
CREATE INDEX idx_tournament_id_fights ON fights(tournament_id);
CREATE INDEX idx_fighter_id_fights ON fights(fighter_id);
CREATE INDEX idx_opponent_id_fights ON fights(opponent_id);
CREATE INDEX idx_fighter_id_achievements ON achievements(fighter_id);
CREATE INDEX idx_event_id_tournaments ON tournaments(event_id);
CREATE INDEX idx_club_id_fighters ON fighters(fighter_club_id);
CREATE INDEX idx_parent_id_clubs ON clubs(club_parent_id);
CREATE INDEX idx_fighter_id_rankings ON rankings(fighter_id);
CREATE INDEX idx_event_country ON events(event_country);
CREATE INDEX idx_club_name ON fighters(fighter_club_name);
CREATE INDEX idx_tournament_id_matches ON match_results(tournament_id);
CREATE INDEX idx_fighter1_matches ON match_results(fighter_id);
CREATE INDEX idx_fighter2_matches ON match_results(opponent_id);

-- After the insert, add these statements:
DO $$
BEGIN
    RAISE NOTICE 'Total achievements loaded: %', (SELECT COUNT(*) FROM achievements);
    RAISE NOTICE 'Distinct fighter_ids in achievements: %', (SELECT COUNT(DISTINCT fighter_id) FROM achievements);
    RAISE NOTICE 'Sample of achievements data:';
    RAISE NOTICE '%', (SELECT string_agg(fighter_id::text || ': ' || achievement_name, E'\n') 
                       FROM (SELECT fighter_id, achievement_name 
                            FROM achievements 
                            WHERE fighter_id != 0 
                            LIMIT 5) t);
END $$;