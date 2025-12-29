import os
import json
import random
from typing import List

try:
    from dotenv import load_dotenv  # optional
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except Exception:
    pass

from faker import Faker

from app.database.session import SessionLocal
from sqlalchemy import text
from app.modules.auth.models.user import User  # ensure mapper
from app.core.security import get_password_hash
from app.modules.proz.models.proz import ProzProfile
# Ensure User is imported so SQLAlchemy registry knows about it for relationships
from app.modules.auth.models.user import User  # noqa: F401
# Ensure task-related relationship classes are registered before mapping ProzProfile
try:
    from app.modules.tasks.models.task import TaskAssignment, TaskNotification  # noqa: F401
except Exception:
    # If tasks module is optional in some environments, ignore
    pass


DEFAULT_STATES = [
    "Texas", "Pennsylvania", "California", "New York", "Florida", "Illinois",
    "Ohio", "Georgia", "North Carolina", "Michigan"
]


def generate_profiles(count: int = 100, states: List[str] = None) -> List[dict]:
    faker = Faker("en_US")
    states = states or DEFAULT_STATES
    data = []
    for _ in range(count):
        first_name = faker.first_name()
        last_name = faker.last_name()
        email = faker.unique.safe_email()
        city = faker.city()
        state = random.choice(states)
        location = f"{city}, {state}"
        years_experience = random.choice([1, 2, 3, 5, 7, 8, 10, 12])
        hourly_rate = round(random.uniform(25, 120), 2)
        availability = random.choice(["full-time", "part-time", "contract", "freelance"])
        phone = faker.numerify(text="+1-###-###-####")
        website = f"https://{faker.domain_name()}"
        linkedin = f"https://www.linkedin.com/in/{faker.user_name()}"
        bio = (
            f"{first_name} {last_name} is a seasoned professional based in {state} with "
            f"{years_experience} years of experience delivering reliable, high-quality solutions."
        )
        education = f"{faker.company()} University — {faker.job()} ({random.choice(['2012–2016', '2015–2019', '2018–2022'])})"
        certifications = random.choice([
            "AWS CCP", "Azure Fundamentals", "PMP", "Scrum Master", "CompTIA Security+"
        ])

        item = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone,
            "bio": bio,
            "location": location,
            "years_experience": years_experience,
            "hourly_rate": hourly_rate,
            "availability": availability,
            "education": education,
            "certifications": certifications,
            "website": website,
            "linkedin": linkedin,
            "preferred_contact_method": "email",
        }
        data.append(item)
    return data


def insert_profiles(profiles: List[dict], create_users: bool = True, default_password: str = "SeedUser@123", verified: bool = False) -> int:
    db = SessionLocal()
    inserted = 0
    try:
        for p in profiles:
            # idempotent: skip if email exists
            exists = db.query(ProzProfile).filter(ProzProfile.email == p["email"]).first()
            if exists:
                continue
            user_id = None
            if create_users:
                # ensure user exists for this email
                user = db.query(User).filter(User.email == p["email"]).first()
                if not user:
                    user = User(
                        email=p["email"],
                        first_name=p["first_name"],
                        last_name=p["last_name"],
                        hashed_password=get_password_hash(default_password),
                        is_active=True,
                        is_superuser=False,
                        is_verified=verified,  # Set user verification status if verified flag is set
                    )
                    db.add(user)
                    db.flush()  # get id
                user_id = user.id
            profile = ProzProfile(
                user_id=user_id,
                first_name=p["first_name"],
                last_name=p["last_name"],
                email=p["email"],
                phone_number=p["phone_number"],
                bio=p["bio"],
                location=p["location"],
                years_experience=p["years_experience"],
                hourly_rate=p["hourly_rate"],
                availability=p["availability"],
                education=p["education"],
                certifications=p["certifications"],
                website=p["website"],
                linkedin=p["linkedin"],
                preferred_contact_method=p["preferred_contact_method"],
                verification_status="verified" if verified else "pending",  # Set verification status
                email_verified=verified,  # Set email verification status
            )
            db.add(profile)
            inserted += 1
        db.commit()
        return inserted
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed US Proz profiles and export JSON")
    parser.add_argument("--count", type=int, default=100, help="Number of profiles to generate")
    parser.add_argument("--states", type=str, default=",".join(DEFAULT_STATES), help="Comma-separated state names")
    parser.add_argument("--out", type=str, default="exports/proz_us_seed.json", help="Output JSON path")
    parser.add_argument("--create-users", action="store_true", help="Also create linked User accounts for each profile")
    parser.add_argument("--password", type=str, default="SeedUser@123", help="Default password for created users")
    parser.add_argument("--verified", action="store_true", help="Create profiles with verified status (verification_status='verified' and email_verified=True)")
    parser.add_argument("--dry", action="store_true", help="Only generate JSON, do not insert into DB")
    args = parser.parse_args()

    states = [s.strip() for s in args.states.split(",") if s.strip()]
    profiles = generate_profiles(args.count, states)

    # Debug: show target DB URL and current row count
    s = SessionLocal()
    try:
        print("Target DB URL:", s.bind.url)
        try:
            before = s.execute(text("SELECT COUNT(*) FROM proz_profiles")).scalar() or 0
        except Exception:
            before = 0
        print(f"Existing proz_profiles rows: {before}")
    finally:
        s.close()

    # Ensure export dir
    out_path = args.out
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"Exported {len(profiles)} profiles -> {out_path}")

    if not args.dry:
        inserted = insert_profiles(profiles, create_users=args.create_users, default_password=args.password, verified=args.verified)
        verification_status = "verified" if args.verified else "pending"
        print(f"Inserted {inserted} new profiles into DB with status '{verification_status}' (skipped existing emails)")
        # Show after count
        s = SessionLocal()
        try:
            after = s.execute(text("SELECT COUNT(*) FROM proz_profiles")).scalar() or 0
            print(f"Now proz_profiles rows: {after}")
        finally:
            s.close()


if __name__ == "__main__":
    main()


