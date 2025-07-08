--- For both : cvs and jobs, 1 to 1
CREATE TABLE preferences
(
    id               integer PRIMARY KEY autoincrement,
    desired_position text,
    employment_type  text,
    desired_salary   integer
);

--- 1 Job to Many ---
CREATE TABLE job_personal_info
(
    id         integer PRIMARY KEY autoincrement,
    age        text,
    location   text,
    relocation text
);

CREATE TABLE job_work_experience
(
    id               integer PRIMARY KEY autoincrement,
    duration         text,
    position         text,
    responsibilities text
);

CREATE TABLE job_education
(
    id             integer PRIMARY KEY autoincrement,
    level          text,
    specialization text
);

CREATE TABLE jobs
(
    id                  integer PRIMARY KEY autoincrement,
    fk_jpi_id           integer,
    fk_p_id             integer,
    fk_jwe_id           integer,
    fk_je_id            integer,
    skills              text,
    skills_technologies text,
    FOREIGN KEY (fk_jpi_id) REFERENCES job_personal_info (id),
    FOREIGN KEY (fk_p_id) REFERENCES preferences (id),
    FOREIGN KEY (fk_jwe_id) REFERENCES job_work_experience (id),
    FOREIGN KEY (fk_je_id) REFERENCES job_education (id)
);


--- 1 CV to Many ---
CREATE TABLE cv_personal_info
(
    id         integer PRIMARY KEY autoincrement,
    name       text,
    age        integer,
    location   text,
    relocation text
);

CREATE TABLE cv_work_experience
(
    id               integer PRIMARY KEY autoincrement,
    company          text,
    period           text,
    duration         text,
    position         text,
    responsibilities text
);

CREATE TABLE cv_education
(
    id             integer PRIMARY KEY autoincrement,
    organization   text,
    level          text,
    year_of_end    integer,
    specialization text
);

CREATE TABLE cv_contacts
(
    id    integer PRIMARY KEY autoincrement,
    phone text,
    email text
);

CREATE TABLE cvs
(
    id                  integer PRIMARY KEY autoincrement,
    fk_cpi_id           integer,
    fk_p_id             integer,
    fk_cwe_id           integer,
    fk_ce_id            integer,
    fk_cc_id            integer,
    skills              text,
    skills_technologies text,
    FOREIGN KEY (fk_cpi_id) REFERENCES cv_personal_info (id),
    FOREIGN KEY (fk_p_id) REFERENCES preferences (id),
    FOREIGN KEY (fk_cwe_id) REFERENCES cv_work_experience (id),
    FOREIGN KEY (fk_ce_id) REFERENCES cv_education (id),
    FOREIGN KEY (fk_cc_id) REFERENCES cv_contacts (id)
);

--- Many to Many ---
CREATE TABLE languages
(
    id    integer PRIMARY KEY autoincrement,
    name  text,
    level text
);

CREATE TABLE on_jobs_languages
(
    job_id      integer NOT NULL,
    language_id integer NOT NULL
);

CREATE TABLE on_cvs_languages
(
    cv_id       integer NOT NULL,
    language_id integer NOT NULL
)
