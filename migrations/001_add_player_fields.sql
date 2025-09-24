-- Migration: Add new fields to players table
-- Description: Add email, weight, height, and sport fields to enhance player management

-- Add new columns to players table
ALTER TABLE public.players
ADD COLUMN email VARCHAR(255),
ADD COLUMN weight_kg DECIMAL(5,2),
ADD COLUMN height_cm INTEGER,
ADD COLUMN sport VARCHAR(50) DEFAULT 'Football';

-- Create index on email for faster lookups
CREATE INDEX idx_players_email ON public.players(email);

-- Add sport types table for future expansion
CREATE TABLE public.sports (
    sport_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    positions TEXT[] NOT NULL
);

-- Insert default sports and their positions
INSERT INTO public.sports (name, positions) VALUES
('Football', ARRAY['Goalkeeper', 'Defender', 'Midfielder', 'Forward']),
('Basketball', ARRAY['Point Guard', 'Shooting Guard', 'Small Forward', 'Power Forward', 'Center']),
('American Football', ARRAY['Quarterback', 'Running Back', 'Wide Receiver', 'Tight End', 'Offensive Line', 'Defensive Line', 'Linebacker', 'Cornerback', 'Safety', 'Kicker', 'Punter']),
('Baseball', ARRAY['Pitcher', 'Catcher', 'First Baseman', 'Second Baseman', 'Third Baseman', 'Shortstop', 'Left Fielder', 'Center Fielder', 'Right Fielder']),
('Hockey', ARRAY['Goaltender', 'Defenseman', 'Left Wing', 'Right Wing', 'Center']),
('Volleyball', ARRAY['Setter', 'Outside Hitter', 'Middle Hitter', 'Opposite Hitter', 'Libero']),
('Tennis', ARRAY['Singles Player', 'Doubles Player']),
('Rugby', ARRAY['Prop', 'Hooker', 'Lock', 'Flanker', 'Number 8', 'Scrum Half', 'Fly Half', 'Wing', 'Centre', 'Fullback']);

-- Update existing players to have Football as default sport if not set
UPDATE public.players SET sport = 'Football' WHERE sport IS NULL;

-- Make sport column NOT NULL after setting defaults
ALTER TABLE public.players ALTER COLUMN sport SET NOT NULL;