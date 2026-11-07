
CREATE TYPE event_mode AS ENUM (
    'presencial',
    'virtual',
    'hibrido'
);

CREATE TYPE event_type AS ENUM (
    'conferencia',
    'taller',
    'foro',
    'concurso',
    'ponencia',
    'presentación',
    'curso',
    'deportiva',
    'cultural',
    'otra',
    'conferencia magistral',
    'visita de campo',
    'panel',
    'exposicion',
    'cátedra patrimonial',
    'mesa de diálogo',
    'capacitación'
);

CREATE FUNCTION is_valid_string_format(t text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
    begin
        return t ~ '^[A-Z\d].*\.$';
    end;
$_$;

COMMENT ON FUNCTION is_valid_string_format(t text) IS 'Validates that the input string starts with an uppercase letter or digit and ends with a period.';

CREATE TABLE entity (
    id uuid DEFAULT uuidv7() NOT NULL,
    name text NOT NULL
);

CREATE VIEW event_modes AS
 SELECT e.enumlabel AS enum_value
   FROM (pg_enum e
     JOIN pg_type t ON ((e.enumtypid = t.oid)))
  WHERE (t.typname = 'event_mode'::name)
  ORDER BY e.enumsortorder;

CREATE VIEW event_types AS
 SELECT e.enumlabel AS enum_value
   FROM (pg_enum e
     JOIN pg_type t ON ((e.enumtypid = t.oid)))
  WHERE (t.typname = 'event_type'::name)
  ORDER BY t.typname, e.enumsortorder;

CREATE TABLE events (
    title text CONSTRAINT activities_title_not_null NOT NULL,
    entity uuid,
    master uuid,
    id uuid DEFAULT uuidv7() CONSTRAINT activities_id_not_null NOT NULL,
    type event_type CONSTRAINT activities_type_not_null NOT NULL,
    CONSTRAINT valid_title CHECK (is_valid_string_format(title))
);

CREATE TABLE locations (
    id uuid DEFAULT uuidv7() CONSTRAINT location_id_not_null NOT NULL,
    session uuid CONSTRAINT location_session_not_null NOT NULL,
    link text,
    CONSTRAINT atleast_link CHECK ((link IS NOT NULL)) NO INHERIT,
    CONSTRAINT is_valid_link CHECK ((link ~ '^https://(?:events\.)?teams\.microsoft\.com/.*$'::text))
);

CREATE TABLE locations_random (
    description text NOT NULL,
    CONSTRAINT valid_description CHECK (is_valid_string_format(description))
)
INHERITS (locations);

CREATE TABLE locations_rooms (
    room uuid NOT NULL
)
INHERITS (locations);

CREATE TABLE person_presents_sessions (
    person uuid NOT NULL,
    session uuid NOT NULL
);

CREATE TABLE persons (
    id uuid DEFAULT uuidv7() NOT NULL,
    name text NOT NULL
);

CREATE TABLE rooms (
    id uuid DEFAULT uuidv7() CONSTRAINT " locations_id_not_null" NOT NULL,
    campus text CONSTRAINT " locations_campus_not_null" NOT NULL,
    building text CONSTRAINT " locations_building_not_null" NOT NULL,
    room text CONSTRAINT " locations_room_not_null" NOT NULL,
    sub text
);

CREATE TABLE sessions (
    id uuid DEFAULT uuidv7() CONSTRAINT session_id_not_null NOT NULL,
    starts timestamp with time zone CONSTRAINT session_starts_not_null NOT NULL,
    ends timestamp with time zone CONSTRAINT session_ends_not_null NOT NULL,
    event uuid CONSTRAINT session_activity_not_null NOT NULL,
    CONSTRAINT starts_before_ends CHECK ((starts < ends))
);

CREATE VIEW sessions_complete AS
 SELECT s.id,
    events.id AS event_id,
    events.title,
    master.name AS master,
    array_agg(presentator.name) AS presentators,
    e.name AS entity,
    s.starts,
    s.ends,
        CASE
            WHEN ((locations.link IS NOT NULL) AND ((rooms.id IS NOT NULL) OR (locations_random.description IS NOT NULL))) THEN 'hibrido'::event_mode
            WHEN (locations.link IS NOT NULL) THEN 'virtual'::event_mode
            ELSE 'presencial'::event_mode
        END AS mode,
    locations.link,
    locations_random.description AS loc_description,
    rooms.campus,
    rooms.building,
    rooms.room
   FROM (((((((((sessions s
     LEFT JOIN events ON ((events.id = s.event)))
     LEFT JOIN locations ON ((locations.session = s.id)))
     LEFT JOIN locations_random ON ((locations.id = locations_random.id)))
     LEFT JOIN locations_rooms ON ((locations.id = locations_rooms.id)))
     LEFT JOIN rooms ON ((locations_rooms.room = rooms.id)))
     LEFT JOIN person_presents_sessions pps ON ((pps.session = s.id)))
     LEFT JOIN persons presentator ON ((presentator.id = pps.person)))
     LEFT JOIN persons master ON ((events.master = master.id)))
     LEFT JOIN entity e ON ((e.id = events.entity)))
  GROUP BY s.id, events.title, master.name, s.starts, s.ends, locations.link, locations_random.description, rooms.campus, rooms.building, rooms.room, rooms.id, e.name, events.id;

CREATE VIEW sessions_query AS
SELECT
    NULL::uuid AS id,
    NULL::uuid AS event_id,
    NULL::text AS title,
    NULL::event_type AS event_type,
    NULL::json AS entity,
    NULL::json AS master,
    NULL::json AS presentators,
    NULL::timestamp with time zone AS starts,
    NULL::timestamp with time zone AS ends,
    NULL::event_mode AS mode,
    NULL::json AS location;

ALTER TABLE ONLY entity
    ADD CONSTRAINT entity_pk PRIMARY KEY (id);

ALTER TABLE ONLY events
    ADD CONSTRAINT events_pk PRIMARY KEY (id);

ALTER TABLE ONLY locations
    ADD CONSTRAINT locations_pk PRIMARY KEY (id);

ALTER TABLE ONLY person_presents_sessions
    ADD CONSTRAINT person_presents_sessions_pk PRIMARY KEY (session, person);

ALTER TABLE ONLY persons
    ADD CONSTRAINT persons_pk PRIMARY KEY (id);

ALTER TABLE ONLY rooms
    ADD CONSTRAINT rooms_pk PRIMARY KEY (id);

ALTER TABLE ONLY sessions
    ADD CONSTRAINT sessions_pk PRIMARY KEY (id);

CREATE OR REPLACE VIEW sessions_query AS
 SELECT s.id,
    events.id AS event_id,
    events.title,
    events.type AS event_type,
    json_build_object('id', e.id, 'name', e.name) AS entity,
    json_build_object('id', master.id, 'name', master.name) AS master,
    json_agg(json_build_object('id', presentator.id, 'name', presentator.name)) FILTER (WHERE (presentator.id IS NOT NULL)) AS presentators,
    s.starts,
    s.ends,
        CASE
            WHEN ((locations.link IS NOT NULL) AND ((rooms.id IS NOT NULL) OR (locations_random.description IS NOT NULL))) THEN 'hibrido'::event_mode
            WHEN (locations.link IS NOT NULL) THEN 'virtual'::event_mode
            ELSE 'presencial'::event_mode
        END AS mode,
        CASE
            WHEN (locations.id IS NOT NULL) THEN json_build_object('id', locations.id, 'session', locations.session, 'link', locations.link, 'description', locations_random.description, 'room',
            CASE
                WHEN (rooms.id IS NOT NULL) THEN json_build_object('id', rooms.id, 'campus', rooms.campus, 'building', rooms.building, 'room', rooms.room, 'sub', rooms.sub)
                ELSE NULL::json
            END)
            ELSE NULL::json
        END AS location
   FROM (((((((((sessions s
     LEFT JOIN events ON ((events.id = s.event)))
     LEFT JOIN locations ON ((locations.session = s.id)))
     LEFT JOIN locations_random ON ((locations.id = locations_random.id)))
     LEFT JOIN locations_rooms ON ((locations.id = locations_rooms.id)))
     LEFT JOIN rooms ON ((locations_rooms.room = rooms.id)))
     LEFT JOIN person_presents_sessions pps ON ((pps.session = s.id)))
     LEFT JOIN persons presentator ON ((presentator.id = pps.person)))
     LEFT JOIN persons master ON ((events.master = master.id)))
     LEFT JOIN entity e ON ((e.id = events.entity)))
  GROUP BY s.id, events.id, e.id, master.id, locations.id, locations_random.description, rooms.id;

ALTER TABLE ONLY events
    ADD CONSTRAINT events_entity_id_fk FOREIGN KEY (entity) REFERENCES entity(id) ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY events
    ADD CONSTRAINT events_persons_id_fk FOREIGN KEY (master) REFERENCES persons(id) ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE ONLY locations_rooms
    ADD CONSTRAINT locations_rooms_rooms_id_fk FOREIGN KEY (room) REFERENCES rooms(id);

ALTER TABLE ONLY locations
    ADD CONSTRAINT locations_sessions_id_fk FOREIGN KEY (session) REFERENCES sessions(id) ON UPDATE CASCADE ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY person_presents_sessions
    ADD CONSTRAINT person_presents_sessions_persons_id_fk FOREIGN KEY (person) REFERENCES persons(id) ON UPDATE CASCADE ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY person_presents_sessions
    ADD CONSTRAINT person_presents_sessions_sessions_id_fk FOREIGN KEY (session) REFERENCES sessions(id) ON UPDATE CASCADE ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY sessions
    ADD CONSTRAINT sessions_events_id_fk FOREIGN KEY (event) REFERENCES events(id) ON UPDATE CASCADE ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

