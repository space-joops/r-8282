-- 경마픽 운영 텔레메트리 스키마
-- 적용: Supabase 대시보드 > SQL Editor에 붙여넣어 실행 (멱등 — 재실행 안전)
-- 보안 모델: RLS 활성 + 정책 없음 → anon/authenticated 완전 차단.
--   쓰기 = 노트북 파이프라인(service 키), 읽기 = /admin 서버 렌더(service 키).

create table if not exists public.ops_runs (
  id           bigint generated always as identity primary key,
  kind         text not null check (kind in ('predict', 'results')),
  target_date  date not null,
  status       text not null check (status in ('success', 'no_change', 'no_races', 'error')),
  source       text not null default 'manual' check (source in ('timer', 'manual')),
  host         text,
  started_at   timestamptz not null,
  finished_at  timestamptz not null default now(),
  duration_sec numeric,
  metrics      jsonb not null default '{}'::jsonb,
  error        text
);

create index if not exists ops_runs_started_at_idx
  on public.ops_runs (started_at desc);

alter table public.ops_runs enable row level security;
-- 의도적으로 정책을 만들지 않는다: service_role만 RLS를 우회해 접근 가능.
