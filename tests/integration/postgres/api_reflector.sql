--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-1.pgdg120+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-1.pgdg120+1)

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

--
-- Name: action; Type: TYPE; Schema: public; Owner: api_reflector
--

CREATE TYPE public.action AS ENUM (
    'DELAY',
    'CALLBACK'
);


ALTER TYPE public.action OWNER TO api_reflector;

--
-- Name: method; Type: TYPE; Schema: public; Owner: api_reflector
--

CREATE TYPE public.method AS ENUM (
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH'
);


ALTER TYPE public.method OWNER TO api_reflector;

--
-- Name: operator; Type: TYPE; Schema: public; Owner: api_reflector
--

CREATE TYPE public.operator AS ENUM (
    'EQUAL',
    'NOT_EQUAL',
    'LESS_THAN',
    'LESS_THAN_EQUAL',
    'GREATER_THAN',
    'GREATER_THAN_EQUAL',
    'IS_EMPTY',
    'IS_NOT_EMPTY',
    'CONTAINS',
    'NOT_CONTAINS'
);


ALTER TYPE public.operator OWNER TO api_reflector;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO api_reflector;

--
-- Name: endpoint; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.endpoint (
    id integer NOT NULL,
    name character varying NOT NULL,
    method public.method NOT NULL,
    path character varying NOT NULL
);


ALTER TABLE public.endpoint OWNER TO api_reflector;

--
-- Name: endpoint_id_seq; Type: SEQUENCE; Schema: public; Owner: api_reflector
--

CREATE SEQUENCE public.endpoint_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.endpoint_id_seq OWNER TO api_reflector;

--
-- Name: endpoint_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: api_reflector
--

ALTER SEQUENCE public.endpoint_id_seq OWNED BY public.endpoint.id;


--
-- Name: response; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.response (
    id integer NOT NULL,
    name character varying NOT NULL,
    endpoint_id integer NOT NULL,
    status_code integer NOT NULL,
    content_type character varying NOT NULL,
    content text NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.response OWNER TO api_reflector;

--
-- Name: response_action; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.response_action (
    id integer NOT NULL,
    response_id integer NOT NULL,
    action public.action NOT NULL,
    arguments character varying[] NOT NULL
);


ALTER TABLE public.response_action OWNER TO api_reflector;

--
-- Name: response_action_id_seq; Type: SEQUENCE; Schema: public; Owner: api_reflector
--

CREATE SEQUENCE public.response_action_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.response_action_id_seq OWNER TO api_reflector;

--
-- Name: response_action_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: api_reflector
--

ALTER SEQUENCE public.response_action_id_seq OWNED BY public.response_action.id;


--
-- Name: response_id_seq; Type: SEQUENCE; Schema: public; Owner: api_reflector
--

CREATE SEQUENCE public.response_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.response_id_seq OWNER TO api_reflector;

--
-- Name: response_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: api_reflector
--

ALTER SEQUENCE public.response_id_seq OWNED BY public.response.id;


--
-- Name: response_rule; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.response_rule (
    id integer NOT NULL,
    response_id integer NOT NULL,
    operator public.operator NOT NULL,
    arguments character varying[] NOT NULL
);


ALTER TABLE public.response_rule OWNER TO api_reflector;

--
-- Name: response_rule_id_seq; Type: SEQUENCE; Schema: public; Owner: api_reflector
--

CREATE SEQUENCE public.response_rule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.response_rule_id_seq OWNER TO api_reflector;

--
-- Name: response_rule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: api_reflector
--

ALTER SEQUENCE public.response_rule_id_seq OWNED BY public.response_rule.id;


--
-- Name: response_tag; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.response_tag (
    response_id integer,
    tag_id integer
);


ALTER TABLE public.response_tag OWNER TO api_reflector;

--
-- Name: tag; Type: TABLE; Schema: public; Owner: api_reflector
--

CREATE TABLE public.tag (
    id integer NOT NULL,
    name character varying NOT NULL
);


ALTER TABLE public.tag OWNER TO api_reflector;

--
-- Name: tag_id_seq; Type: SEQUENCE; Schema: public; Owner: api_reflector
--

CREATE SEQUENCE public.tag_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_id_seq OWNER TO api_reflector;

--
-- Name: tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: api_reflector
--

ALTER SEQUENCE public.tag_id_seq OWNED BY public.tag.id;


--
-- Name: endpoint id; Type: DEFAULT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.endpoint ALTER COLUMN id SET DEFAULT nextval('public.endpoint_id_seq'::regclass);


--
-- Name: response id; Type: DEFAULT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response ALTER COLUMN id SET DEFAULT nextval('public.response_id_seq'::regclass);


--
-- Name: response_action id; Type: DEFAULT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_action ALTER COLUMN id SET DEFAULT nextval('public.response_action_id_seq'::regclass);


--
-- Name: response_rule id; Type: DEFAULT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_rule ALTER COLUMN id SET DEFAULT nextval('public.response_rule_id_seq'::regclass);


--
-- Name: tag id; Type: DEFAULT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.tag ALTER COLUMN id SET DEFAULT nextval('public.tag_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.alembic_version (version_num) FROM stdin;
d42bddfac4f1
\.


--
-- Data for Name: endpoint; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.endpoint (id, name, method, path) FROM stdin;
1	Get Europa Configuration	GET	/europa/configuration
\.


--
-- Data for Name: response; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.response (id, name, endpoint_id, status_code, content_type, content, is_active) FROM stdin;
1	Europa Wasabi Club	1	200	application/json	{\r\n    "merchant_url": "http://api-reflector:6502/mock/wasabi-api",\r\n    "callback_url": "http://api-reflector:6502/mock/wasabi-callback",\r\n    "retry_limit": 3,\r\n    "log_level": 1,\r\n    "country": "GB",\r\n    "security_credentials": {\r\n        "inbound": {\r\n            "service": 0,\r\n            "credentials": [{\r\n                "credential_type": "compound_key",\r\n                "value": "key",\r\n                "storage_key": "test-wasabi-key"\r\n            }]\r\n        },\r\n        "outbound": {\r\n            "service": 0,\r\n            "credentials": {}\r\n        }\r\n    }\r\n}	t
\.


--
-- Data for Name: response_action; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.response_action (id, response_id, action, arguments) FROM stdin;
\.


--
-- Data for Name: response_rule; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.response_rule (id, response_id, operator, arguments) FROM stdin;
1	1	EQUAL	{"{{request.query.merchant_id}}",wasabi-club}
2	1	EQUAL	{"{{request.query.handler_type}}",3}
\.


--
-- Data for Name: response_tag; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.response_tag (response_id, tag_id) FROM stdin;
1	1
\.


--
-- Data for Name: tag; Type: TABLE DATA; Schema: public; Owner: api_reflector
--

COPY public.tag (id, name) FROM stdin;
1	europa
\.


--
-- Name: endpoint_id_seq; Type: SEQUENCE SET; Schema: public; Owner: api_reflector
--

SELECT pg_catalog.setval('public.endpoint_id_seq', 1, true);


--
-- Name: response_action_id_seq; Type: SEQUENCE SET; Schema: public; Owner: api_reflector
--

SELECT pg_catalog.setval('public.response_action_id_seq', 1, false);


--
-- Name: response_id_seq; Type: SEQUENCE SET; Schema: public; Owner: api_reflector
--

SELECT pg_catalog.setval('public.response_id_seq', 1, true);


--
-- Name: response_rule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: api_reflector
--

SELECT pg_catalog.setval('public.response_rule_id_seq', 2, true);


--
-- Name: tag_id_seq; Type: SEQUENCE SET; Schema: public; Owner: api_reflector
--

SELECT pg_catalog.setval('public.tag_id_seq', 1, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: endpoint endpoint_method_path_key; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.endpoint
    ADD CONSTRAINT endpoint_method_path_key UNIQUE (method, path);


--
-- Name: endpoint endpoint_pkey; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.endpoint
    ADD CONSTRAINT endpoint_pkey PRIMARY KEY (id);


--
-- Name: response_action response_action_pkey; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_action
    ADD CONSTRAINT response_action_pkey PRIMARY KEY (id);


--
-- Name: response response_pkey; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response
    ADD CONSTRAINT response_pkey PRIMARY KEY (id);


--
-- Name: response_rule response_rule_pkey; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_rule
    ADD CONSTRAINT response_rule_pkey PRIMARY KEY (id);


--
-- Name: tag tag_name_key; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.tag
    ADD CONSTRAINT tag_name_key UNIQUE (name);


--
-- Name: tag tag_pkey; Type: CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (id);


--
-- Name: response_action response_action_response_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_action
    ADD CONSTRAINT response_action_response_id_fkey FOREIGN KEY (response_id) REFERENCES public.response(id);


--
-- Name: response response_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response
    ADD CONSTRAINT response_endpoint_id_fkey FOREIGN KEY (endpoint_id) REFERENCES public.endpoint(id);


--
-- Name: response_rule response_rule_response_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_rule
    ADD CONSTRAINT response_rule_response_id_fkey FOREIGN KEY (response_id) REFERENCES public.response(id);


--
-- Name: response_tag response_tag_response_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_tag
    ADD CONSTRAINT response_tag_response_id_fkey FOREIGN KEY (response_id) REFERENCES public.response(id);


--
-- Name: response_tag response_tag_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: api_reflector
--

ALTER TABLE ONLY public.response_tag
    ADD CONSTRAINT response_tag_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tag(id);


--
-- PostgreSQL database dump complete
--

