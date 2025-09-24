from ..repositories.organizations import OrganizationRepository
from ..schemas.organizations import CreateOrganization, OrganizationDTO


class OrganizationService:
    def __init__(self):
        from flask import g
        self.organizations = OrganizationRepository(g.db_session)

    def create_organization(self, cmd: CreateOrganization) -> OrganizationDTO:
        organization = self.organizations.create_organization(
            cmd.name, cmd.domain, cmd.owner_email
        )
        self.organizations.s.commit()
        return OrganizationDTO.from_db(organization)
