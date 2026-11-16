# Disaster Recovery & Firestore Backup Runbook

## Overview
This runbook provides step-by-step procedures for scheduled backups, emergency exports, and data recovery for **VRS Corporate Solutions** portal database and Cloud Storage.

---

## 1. Authoritative Backup Schedule

| Frequency | Target Storage | Retention Policy | Purpose |
| :--- | :--- | :--- | :--- |
| **Daily (Automated)** | Cloud Storage (`asia-south1`) | 30 Days | Point-in-time recovery for operational mistakes |
| **Weekly (Snapshots)** | Coldline / Archive Bucket | 90 Days | Regulatory compliance & audit history |
| **Monthly (Encrypted Archive)** | Offline Secure Storage | 1 Year | Disaster recovery & DPDP statutory audits |

---

## 2. Running a Manual Backup

Before major system migrations or schema changes:

1. Open PowerShell / Terminal in the project root.
2. Authenticate with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```
3. Run the export script:
   ```bash
   GOOGLE_CLOUD_PROJECT=vrs-dra-portal-staging npx tsx scripts/backup-firestore.ts
   ```
4. Verify the generated manifest in `backups/firestore-<timestamp>/_manifest.json`.

---

## 3. Google Cloud Managed Managed Firestore Export

For scheduled serverless backups via Google Cloud:

```bash
gcloud firestore export gs://vrs-dra-backups-staging/$(date +%Y-%m-%d) \
  --project=vrs-dra-portal-staging
```

---

## 4. Disaster Recovery & Restoration Procedure

In the event of accidental data deletion or hardware failure:

1. **Verify Integrity of the Backup**:
   - Check the `_manifest.json` file for expected document counts.
2. **Restore to Staging First**:
   - Always perform a test import into staging before touching production:
   ```bash
   gcloud firestore import gs://vrs-dra-backups-staging/<backup-date> \
     --project=vrs-dra-portal-staging
   ```
3. **Verify Integrity Post-Import**:
   - Verify candidate counts, vacancies, and certificate verification records.
4. **Log Incident & Recovery Event**:
   - Document root cause and recovery duration in the portal security log.
