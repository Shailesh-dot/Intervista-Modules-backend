-- 1. Master questions table
CREATE TABLE IF NOT EXISTS aptitude_questions (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);

-- 2. Quiz results table
CREATE TABLE IF NOT EXISTS quiz_results (
    id SERIAL PRIMARY KEY,
    correct INTEGER NOT NULL DEFAULT 0,
    wrong INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Quiz answers table
CREATE TABLE IF NOT EXISTS quiz_answers (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES quiz_results(id) ON DELETE CASCADE,
    question_id INTEGER,
    question_text TEXT,
    user_answer VARCHAR(10),
    correct_answer VARCHAR(10),
    is_correct BOOLEAN,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Individual topic tables
CREATE TABLE IF NOT EXISTS topic_02_data_interpretation (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_03_probability (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_04_permutation_combination (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_09_data_sufficiency (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_10_logical_puzzles (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_11_number_system (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_12_hcf_lcm (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_13_percentages (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_14 (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q25_missing_figure (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q26_figure_series (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q27_paper_folding (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q28_cube_dice (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q29_embedded_figures (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_q30_calendar_clock (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_01_direction_sense (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_02_coding_decoding (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_03_number_series (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_04_blood_relations (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_05_order_ranking (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_06_syllogism (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_08_inequalities (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_14_ratio_proportion (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_15_profit_loss_discounts (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_16_averages (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_17_time_work (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_22_mirror_image (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_23_water_image (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_24_shadow_light (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);
CREATE TABLE IF NOT EXISTS topic_25_missing_figure (
    id SERIAL PRIMARY KEY,
    question TEXT UNIQUE,
    options TEXT,
    correct_answer VARCHAR(10),
    explanation TEXT,
    category VARCHAR(200),
    source VARCHAR(200)
);