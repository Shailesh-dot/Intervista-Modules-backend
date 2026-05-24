--
-- PostgreSQL database dump
--

\restrict BtANFOPAgmEd4m6DeXewfPR0YvYKhiTYfJF5dddUjwjIaGA6TxgefBF1IJcwLsY

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: assessment_sessions; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.assessment_sessions (
    session_id character varying NOT NULL,
    candidate_id character varying NOT NULL,
    status character varying,
    start_time timestamp with time zone,
    end_time timestamp with time zone NOT NULL,
    duration_minutes integer NOT NULL
);


ALTER TABLE public.assessment_sessions OWNER TO coding_platform;

--
-- Name: questions; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.questions (
    id character varying NOT NULL,
    title character varying NOT NULL,
    description character varying NOT NULL,
    difficulty character varying NOT NULL,
    examples jsonb,
    constraints jsonb,
    boilerplates jsonb,
    metadata_obj jsonb,
    allowed_languages jsonb,
    created_by character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    CONSTRAINT difficulty_check CHECK (((difficulty)::text = ANY ((ARRAY['Easy'::character varying, 'Medium'::character varying, 'Hard'::character varying])::text[])))
);


ALTER TABLE public.questions OWNER TO coding_platform;

--
-- Name: submission_results; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.submission_results (
    id integer NOT NULL,
    submission_id character varying NOT NULL,
    test_case_id integer,
    status character varying,
    stdout character varying,
    stderr character varying,
    compile_output character varying,
    execution_time double precision
);


ALTER TABLE public.submission_results OWNER TO coding_platform;

--
-- Name: submission_results_id_seq; Type: SEQUENCE; Schema: public; Owner: coding_platform
--

CREATE SEQUENCE public.submission_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.submission_results_id_seq OWNER TO coding_platform;

--
-- Name: submission_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: coding_platform
--

ALTER SEQUENCE public.submission_results_id_seq OWNED BY public.submission_results.id;


--
-- Name: submissions; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.submissions (
    submission_id character varying NOT NULL,
    candidate_id character varying,
    question_id character varying NOT NULL,
    session_id character varying,
    language character varying NOT NULL,
    source_code character varying NOT NULL,
    status character varying,
    job_status character varying,
    judge0_token character varying,
    total_test_cases integer,
    passed_test_cases integer,
    score double precision,
    execution_time double precision,
    memory double precision,
    compile_output character varying,
    submitted_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.submissions OWNER TO coding_platform;

--
-- Name: test_cases; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.test_cases (
    id integer NOT NULL,
    question_id character varying NOT NULL,
    input_data character varying NOT NULL,
    expected_output character varying NOT NULL,
    is_sample boolean,
    is_hidden boolean,
    weight integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT sample_hidden_check CHECK ((((is_sample = true) AND (is_hidden = false)) OR ((is_sample = false) AND (is_hidden = true))))
);


ALTER TABLE public.test_cases OWNER TO coding_platform;

--
-- Name: test_cases_id_seq; Type: SEQUENCE; Schema: public; Owner: coding_platform
--

CREATE SEQUENCE public.test_cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.test_cases_id_seq OWNER TO coding_platform;

--
-- Name: test_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: coding_platform
--

ALTER SEQUENCE public.test_cases_id_seq OWNED BY public.test_cases.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: coding_platform
--

CREATE TABLE public.users (
    user_id character varying NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    role character varying DEFAULT 'user'::character varying NOT NULL,
    name character varying,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'admin'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO coding_platform;

--
-- Name: submission_results id; Type: DEFAULT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submission_results ALTER COLUMN id SET DEFAULT nextval('public.submission_results_id_seq'::regclass);


--
-- Name: test_cases id; Type: DEFAULT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.test_cases ALTER COLUMN id SET DEFAULT nextval('public.test_cases_id_seq'::regclass);


--
-- Name: assessment_sessions assessment_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT assessment_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- Name: submission_results submission_results_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submission_results
    ADD CONSTRAINT submission_results_pkey PRIMARY KEY (id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (submission_id);


--
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: ix_assessment_sessions_candidate_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_assessment_sessions_candidate_id ON public.assessment_sessions USING btree (candidate_id);


--
-- Name: ix_questions_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_questions_id ON public.questions USING btree (id);


--
-- Name: ix_submissions_candidate_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_submissions_candidate_id ON public.submissions USING btree (candidate_id);


--
-- Name: ix_submissions_question_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_submissions_question_id ON public.submissions USING btree (question_id);


--
-- Name: ix_submissions_submission_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_submissions_submission_id ON public.submissions USING btree (submission_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_user_id; Type: INDEX; Schema: public; Owner: coding_platform
--

CREATE INDEX ix_users_user_id ON public.users USING btree (user_id);


--
-- Name: questions questions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: submission_results submission_results_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submission_results
    ADD CONSTRAINT submission_results_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(submission_id) ON DELETE CASCADE;


--
-- Name: submission_results submission_results_test_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submission_results
    ADD CONSTRAINT submission_results_test_case_id_fkey FOREIGN KEY (test_case_id) REFERENCES public.test_cases(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.assessment_sessions(session_id) ON DELETE CASCADE;


--
-- Name: test_cases test_cases_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: coding_platform
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict BtANFOPAgmEd4m6DeXewfPR0YvYKhiTYfJF5dddUjwjIaGA6TxgefBF1IJcwLsY

