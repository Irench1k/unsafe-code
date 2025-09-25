from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Organization


class OrganizationRepository:
    def __init__(self, session: Session):
        self.s = session

    def create_organization(self, name: str, domain: str, owner_email: str) -> Organization:
        """Create a new organization"""
        org = Organization(name=name, domain=domain, owner_email=owner_email)
        self.s.add(org)
        return org

    def get_by_domain(self, domain: str) -> Organization | None:
        """Get organization by domain"""
        stmt = select(Organization).where(Organization.domain == domain)
        return self.s.scalars(stmt).first()

    def list_all(self) -> list[Organization]:
        """List all organizations - for admin purposes"""
        stmt = select(Organization)
        return list(self.s.scalars(stmt).all())

    def is_owner(self, domain: str, user_email: str) -> bool:
        """Check if user is owner of organization"""
        org = self.get_by_domain(domain)
        return org is not None and org.owner_email == user_email

    def get_organization_for_email(self, email: str) -> Organization | None:
        """Get organization for email address"""
        if '@' not in email:
            return None

        domain = email.split('@')[-1]
        return self.get_by_domain(domain)
