from sqlalchemy import select, exists, and_
from sqlalchemy.orm import Session
from ..models import Organization


class OrganizationRepository:
    def __init__(self, session: Session):
        self.s = session

    def get_by_id(self, org_id: int) -> Organization | None:
        return self.s.get(Organization, org_id)

    def get_by_domain(self, domain: str) -> Organization | None:
        stmt = select(Organization).where(Organization.domain == domain)
        return self.s.scalars(stmt).first()

    def is_owner(self, org_id: int, user_email: str) -> bool:
        stmt = select(
            exists().where(
                and_(Organization.id == org_id, Organization.owner_email == user_email)
            )
        )
        return self.s.scalar(stmt)
