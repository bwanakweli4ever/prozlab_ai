import os
import json
from typing import List, Set

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except Exception:
    pass

from app.database.session import SessionLocal
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile


def delete_verified_users(db) -> int:
    to_delete = db.query(User).filter(User.is_verified == True).all()  # noqa: E712
    count = len(to_delete)
    for u in to_delete:
        db.delete(u)
    db.commit()
    return count


def verify_proz_from_json(db, json_path: str) -> int:
    with open(json_path, 'r') as f:
        data = json.load(f)
    emails: Set[str] = set()
    if isinstance(data, list):
        for item in data:
            email = (item.get('email') or '').strip()
            if email:
                emails.add(email)
    count = 0
    if not emails:
        return 0
    q = db.query(ProzProfile).filter(ProzProfile.email.in_(list(emails)))
    for p in q.all():
        if p.verification_status != 'verified':
            p.verification_status = 'verified'
            count += 1
    db.commit()
    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Delete verified users and verify seeded Proz profiles")
    parser.add_argument('--delete-verified-users', action='store_true', help='Delete all users with is_verified=true')
    parser.add_argument('--verify-from-json', type=str, help='Path to JSON export produced by seeding to verify those Proz profiles')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.delete_verified_users:
            n = delete_verified_users(db)
            print(f"Deleted {n} verified users")
        if args.verify_from_json:
            n = verify_proz_from_json(db, args.verify_from_json)
            print(f"Verified {n} Proz profiles from {args.verify_from_json}")
        if not args.delete_verified_users and not args.verify_from_json:
            print('No action taken. Use --delete-verified-users and/or --verify-from-json <path>.')
    finally:
        db.close()


if __name__ == '__main__':
    main()


