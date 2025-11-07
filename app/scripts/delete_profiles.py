import os
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except Exception:
    pass

from sqlalchemy import func

from app.database.session import SessionLocal
from app.modules.proz.models.proz import ProzProfile


def delete_by_names(names: List[str]) -> int:
    db = SessionLocal()
    deleted = 0
    try:
        for full in names:
            needle = (full or '').strip()
            if not needle:
                continue
            # Case-insensitive match on concatenated name or either part
            parts = needle.split()
            q = db.query(ProzProfile)
            if len(parts) >= 2:
                first = parts[0]
                last = parts[-1]
                q = q.filter(
                    (func.lower(ProzProfile.first_name) == func.lower(first)) &
                    (func.lower(ProzProfile.last_name) == func.lower(last))
                )
            else:
                q = q.filter(
                    (func.lower(ProzProfile.first_name) == func.lower(needle)) |
                    (func.lower(ProzProfile.last_name) == func.lower(needle))
                )
            for p in q.all():
                db.delete(p)
                deleted += 1
        db.commit()
        return deleted
    finally:
        db.close()


def delete_by_emails(emails: List[str]) -> int:
    db = SessionLocal()
    deleted = 0
    try:
        for e in emails:
            e = (e or '').strip()
            if not e:
                continue
            q = db.query(ProzProfile).filter(func.lower(ProzProfile.email) == func.lower(e))
            for p in q.all():
                db.delete(p)
                deleted += 1
        db.commit()
        return deleted
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Delete Proz profiles by name or email')
    parser.add_argument('--names', type=str, help='Comma-separated full names to delete (case-insensitive)')
    parser.add_argument('--emails', type=str, help='Comma-separated emails to delete (case-insensitive)')
    args = parser.parse_args()

    total = 0
    if args.names:
        names = [n.strip() for n in args.names.split(',') if n.strip()]
        total += delete_by_names(names)
    if args.emails:
        emails = [e.strip() for e in args.emails.split(',') if e.strip()]
        total += delete_by_emails(emails)
    if total == 0 and not (args.names or args.emails):
        print('No action taken. Use --names and/or --emails')
    else:
        print(f'Deleted {total} profiles')


if __name__ == '__main__':
    main()


