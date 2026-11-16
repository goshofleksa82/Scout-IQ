"""PostgreSQL audit DDL shared by Alembic and real-database tests. No config imports."""
TIMESTAMP_TABLES=('players','clubs','competitions','seasons','player_club_memberships','matches','match_events')
AUDIT_TABLES={name:'id' for name in (*TIMESTAMP_TABLES,'users','player_match_stats','import_batches','import_identities','scoring_models','watchlists','scouting_reports','data_quality_runs')}
AUDIT_TABLES.update(match_participants='match_id,player_id',watchlist_items='watchlist_id,player_id',scouting_report_versions='report_id,version')
CURRENT_AUDIT_TABLES={**AUDIT_TABLES,'beta_feedback':'id'}

FUNCTIONS=r'''
CREATE OR REPLACE FUNCTION scoutiq_touch_updated() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW IS DISTINCT FROM OLD THEN NEW.updated_at=statement_timestamp(); END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION scoutiq_capture_audit() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE old_data jsonb; new_data jsonb; payload jsonb; key_data jsonb; changed jsonb; actor text;
BEGIN
  -- Only disposable automated-test cleanup can bypass trigger logging.
  IF current_database()='scoutiq_test' AND current_setting('scoutiq.test_cleanup',true)='on' THEN
    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
  END IF;
  old_data=CASE WHEN TG_OP='INSERT' THEN NULL ELSE to_jsonb(OLD) END;
  new_data=CASE WHEN TG_OP='DELETE' THEN NULL ELSE to_jsonb(NEW) END;
  IF TG_TABLE_NAME='users' THEN
    old_data=old_data-ARRAY['username','email','hashed_password'];
    new_data=new_data-ARRAY['username','email','hashed_password'];
  ELSIF TG_TABLE_NAME='watchlists' THEN
    old_data=old_data-ARRAY['name','description'];new_data=new_data-ARRAY['name','description'];
  ELSIF TG_TABLE_NAME='scouting_reports' THEN
    old_data=old_data-ARRAY['title','observed_on','context','technical','tactical','physical','mental','summary','recommendation'];
    new_data=new_data-ARRAY['title','observed_on','context','technical','tactical','physical','mental','summary','recommendation'];
  ELSIF TG_TABLE_NAME='scouting_report_versions' THEN
    old_data=old_data-'content';new_data=new_data-'content';
  ELSIF TG_TABLE_NAME IN ('import_batches','data_quality_runs') THEN
    old_data=old_data-ARRAY['report','summary'];new_data=new_data-ARRAY['report','summary'];
  ELSIF TG_TABLE_NAME='beta_feedback' THEN
    old_data=old_data-ARRAY['message','admin_note'];new_data=new_data-ARRAY['message','admin_note'];
  END IF;
  payload=coalesce(new_data,old_data);
  SELECT jsonb_object_agg(k,payload->k) INTO key_data FROM unnest(string_to_array(TG_ARGV[0],',')) AS k;
  SELECT coalesce(jsonb_agg(k ORDER BY k),'[]'::jsonb) INTO changed FROM jsonb_object_keys(coalesce(new_data,'{}'::jsonb)||coalesce(old_data,'{}'::jsonb)) AS k WHERE old_data->k IS DISTINCT FROM new_data->k;
  -- Record updates even when changed private fields are deliberately omitted.
  actor=current_setting('scoutiq.actor_id',true);
  EXECUTE format('INSERT INTO %I.audit_logs (actor_id,entity,action,record_key,before,after,changed_fields,source) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)',TG_TABLE_SCHEMA)
    USING nullif(actor,'')::integer,TG_TABLE_NAME,CASE TG_OP WHEN 'INSERT' THEN 'create' WHEN 'UPDATE' THEN 'update' ELSE 'delete' END,key_data,old_data,new_data,changed,CASE WHEN nullif(actor,'') IS NULL THEN 'system_or_unattributed' ELSE 'authenticated_api' END;
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE OR REPLACE FUNCTION scoutiq_protect_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_database()='scoutiq_test' AND current_setting('scoutiq.test_cleanup',true)='on' THEN RETURN OLD; END IF;
  RAISE EXCEPTION 'Audit records are append-only';
END $$;
'''


def install_audit_triggers(execute,include_beta=False):
    execute(FUNCTIONS)
    def trigger(table,name,definition):
        # Qualify every table/function to prevent search_path falling through to
        # an unrelated schema during a fresh or historical migration.
        execute(f'''DO $install$ DECLARE ns text=current_schema(); BEGIN
          EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I','{name}',ns,'{table}');
          EXECUTE format('{definition}', '{name}',ns,'{table}',ns);
        END $install$;''')
    for table,keys in (CURRENT_AUDIT_TABLES if include_beta else AUDIT_TABLES).items():
        trigger(table,'scoutiq_audit_row',f"CREATE TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON %I.%I FOR EACH ROW EXECUTE FUNCTION %I.scoutiq_capture_audit(''{keys}'')")
    for table in (*TIMESTAMP_TABLES,'player_match_stats','watchlists','scouting_reports',*(('beta_feedback',) if include_beta else ())):
        trigger(table,'scoutiq_touch_row','CREATE TRIGGER %I BEFORE UPDATE ON %I.%I FOR EACH ROW EXECUTE FUNCTION %I.scoutiq_touch_updated()')
    trigger('audit_logs','scoutiq_audit_immutable','CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I.%I FOR EACH ROW EXECUTE FUNCTION %I.scoutiq_protect_audit()')
