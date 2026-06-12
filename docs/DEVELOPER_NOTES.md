# Developer Notes and Assumptions

## Assumptions

1. The Excel workbook will be available in the repository/Codex directory when implementation starts.
2. The workbook contains at least an input/data-entry sheet and a budget sheet.
3. Some workbook columns may be in Persian.
4. The first version is local-first and deployment can be handled later.
5. The database should not literally be Excel. Excel is used for initial import and later export. The application database should be SQLite locally and PostgreSQL-ready later.
6. The admin needs full control over users, roles, teams, permissions, invoice data, and exports.
7. Referral and SMS should be separate spend buckets, not hidden inside team totals.

## Why Django

Django is recommended because this is an internal business dashboard with authentication, admin management, forms, file uploads, permissions, and reports. Django gives these features faster and with less custom infrastructure than a FastAPI + separate frontend stack.

## Persian UI

The implementation docs are English. Later, UI labels can be translated to Persian using Django internationalization or a simple label dictionary. Do not mix Persian model names into code.

## Deployment Later

Do not spend first-version time on deployment. Build the local app first. Later deployment options can include:

- single VM with PostgreSQL
- Docker Compose
- AWS EC2 + RDS
- ECS/Fargate + RDS + S3 for media

## Data Safety

Until production storage is configured, uploaded invoice/payment proof files are local media files. Do not put sensitive production data into a public repository.
