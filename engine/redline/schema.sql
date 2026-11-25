create table if not exists classes (
  code        char(6) primary key,
  name        text not null check (char_length(name) between 1 and 80),
  created_at  timestamptz not null default now()
);
create table if not exists misconception_events (
  id               bigserial primary key,
  class_code       char(6) not null references classes(code) on delete cascade,
  misconception_id text not null,
  topic            text not null default 'algebra',
  created_at       timestamptz not null default now()
);
create index if not exists idx_events_class_time on misconception_events (class_code, created_at desc);
