# Production hardening release checklist

This release is deliberately data-preserving. It contains no schema migration
and does not run data repair automatically.

## Before deployment

1. Keep `main` untouched. Deploy the reviewed `school-update` commit to a
   staging environment or a maintenance window first.
2. Take and verify a database backup. Keep the backup reference with the
   deployment record.
3. Prepare the production host values using `.env.example` as the variable
   names. The configuration switchover and credential rotation remain a
   separately reviewed release; do not remove or rotate existing credentials
   until the host values have been checked by the deployment owner.
4. Run the read-only audits for the intended academic period:

   ```bash
   python manage.py audit_student_integrity --year <year> --term <term>
   python manage.py audit_student_credits
   ```

5. Save the audit output. Do not use `--repair-safe` until the dry run has been
   reviewed and a rollback backup is known to work.

## Deployment checks

```bash
python manage.py check --settings=core.settings.production
python manage.py makemigrations --check --dry-run --settings=core.settings.production
python manage.py migrate --plan --settings=core.settings.production
python manage.py collectstatic --noinput --settings=core.settings.production
```

No new migration is expected from this release. If a migration plan contains
unexpected operations, stop the rollout and investigate before applying it.

## Smoke test after deployment

1. Add or promote one test learner in a non-production academic period and
   confirm one `ClassRegister`, matching student snapshot, and one
   `StudentBill` exist.
2. Open Fees Status for that period and confirm a registered learner without a
   bill appears as **No Bill** and is included in the warning count.
3. Apply part of an overpayment, then attempt a second application. The second
   application must be limited to the remaining source credit.
4. Edit the dates of the current term. Confirm this does not start a rollover.
5. Try to delete a class, stream, academic class, or bill item with history.
   The interface must block it and name the protected references.

## Deliberately deferred work

- Credential rotation and removal of legacy in-repository fallback values need
  coordinated hosting access; perform them only after the environment values
  are confirmed.
- The planned rollover preview/confirm workflow, broad UI redesign, static
  source consolidation, and database uniqueness constraints remain separate,
  reviewed releases. They should not be bundled into this data-integrity patch.
