"""Database seeding with SpongeBob-themed test data (from r04 example)."""

import bcrypt
from sqlalchemy.orm import Session

from .models import Group, GroupMember, Message, Organization, RoleEnum, User


def seed_database(session: Session) -> None:
    """Seed the database with SpongeBob-themed test data."""

    # Clear existing data (for development)
    session.query(Message).delete()
    session.query(GroupMember).delete()
    session.query(Group).delete()
    session.query(User).delete()
    session.query(Organization).delete()

    # Create organizations
    krusty_krab = Organization(
        name="The Krusty Krab",
        domain="krusty-krab.sea",
        owner_email="mr.krabs@krusty-krab.sea"
    )

    chum_bucket = Organization(
        name="The Chum Bucket",
        domain="chum-bucket.sea",
        owner_email="plankton@chum-bucket.sea"
    )

    session.add_all([krusty_krab, chum_bucket])
    session.flush()

    # Create users with hashed passwords
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    users = [
        User(
            email="spongebob@krusty-krab.sea",
            first_name="SpongeBob",
            last_name="SquarePants",
            password_hash=hash_password("bikinibottom")
        ),
        User(
            email="squidward@krusty-krab.sea",
            first_name="Squidward",
            last_name="Tentacles",
            password_hash=hash_password("the-best-manager")
        ),
        User(
            email="mr.krabs@krusty-krab.sea",
            first_name="Eugene",
            last_name="Krabs",
            password_hash=hash_password("$$$money$$$")
        ),
        User(
            email="plankton@chum-bucket.sea",
            first_name="Sheldon",
            last_name="Plankton",
            password_hash=hash_password("burgers-are-yummy")
        )
    ]

    session.add_all(users)
    session.flush()

    # Create groups
    groups = [
        Group(
            name="staff@krusty-krab.sea",
            description="Krusty Krab staff members"
        ),
        Group(
            name="managers@krusty-krab.sea",
            description="Krusty Krab management team"
        ),
        Group(
            name="staff@chum-bucket.sea",
            description="Chum Bucket staff (just Plankton)"
        )
    ]

    session.add_all(groups)
    session.flush()

    # Create group memberships
    memberships = [
        # Krusty Krab staff
        GroupMember(user_email="spongebob@krusty-krab.sea", group_name="staff@krusty-krab.sea", role=RoleEnum.member),
        GroupMember(user_email="squidward@krusty-krab.sea", group_name="staff@krusty-krab.sea", role=RoleEnum.member),
        GroupMember(user_email="mr.krabs@krusty-krab.sea", group_name="staff@krusty-krab.sea", role=RoleEnum.admin),

        # Krusty Krab managers
        GroupMember(user_email="squidward@krusty-krab.sea", group_name="managers@krusty-krab.sea", role=RoleEnum.member),
        GroupMember(user_email="mr.krabs@krusty-krab.sea", group_name="managers@krusty-krab.sea", role=RoleEnum.admin),

        # Chum Bucket staff
        GroupMember(user_email="plankton@chum-bucket.sea", group_name="staff@chum-bucket.sea", role=RoleEnum.admin)
    ]

    session.add_all(memberships)
    session.flush()

    # Create messages
    messages = [
        # User messages
        Message(
            from_user="hackerschool@deepweb.sea",
            recipient_user="plankton@chum-bucket.sea",
            message="Congratulations Plankton! You've completed 'Email Hacking 101'."
        ),
        Message(
            from_user="plankton@chum-bucket.sea",
            recipient_user="squidward@krusty-krab.sea",
            message="Hey Squidward, I'll pay you $1000 if you just happen to 'accidentally' leave the formula where I can see it. You deserve better than working for that cheap crab!"
        ),

        # Group messages
        Message(
            from_user="mr.krabs@krusty-krab.sea",
            recipient_group="staff@krusty-krab.sea",
            message="I am updating the safe password to '123456'. Do not tell anyone!"
        ),
        Message(
            from_user="mr.krabs@krusty-krab.sea",
            recipient_group="managers@krusty-krab.sea",
            message="Meeting with the board of directors tomorrow at 10 AM. Be on time!"
        ),
        Message(
            from_user="plankton@chum-bucket.sea",
            recipient_group="staff@chum-bucket.sea",
            message="To my future self, don't forget to steal the formula!"
        )
    ]

    session.add_all(messages)
    session.commit()

    print("Database seeded successfully with SpongeBob-themed data!")
    print("Organizations:")
    print("  - The Krusty Krab (krusty-krab.sea) - owned by mr.krabs@krusty-krab.sea")
    print("  - The Chum Bucket (chum-bucket.sea) - owned by plankton@chum-bucket.sea")
    print("\nUsers:")
    for user in users:
        print(f"  - {user.first_name} {user.last_name} ({user.email})")
    print("\nGroups:")
    for group in groups:
        print(f"  - {group.name}: {group.description}")
