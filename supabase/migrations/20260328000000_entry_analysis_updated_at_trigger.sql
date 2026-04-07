-- Auto-update entry_analysis.updated_at whenever a row is modified.

create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_entry_analysis_updated_at
    before update on public.entry_analysis
    for each row execute function public.set_updated_at();
