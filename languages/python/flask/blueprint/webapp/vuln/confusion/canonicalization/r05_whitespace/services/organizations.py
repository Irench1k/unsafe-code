from ..db import make_session
from ..repositories.organizations import OrganizationRepository
from ..schemas.organizations import CreateOrganization, OrganizationDTO


class UserService:
    def __init__(self):
        self.s = make_session()
        self.organizations = OrganizationRepository(self.s)

    def create_organization(self, cmd: CreateOrganization) -> OrganizationDTO:
        organization = self.organizations.create_organization(
            cmd.name, cmd.domain, cmd.owner_email
        )
        return OrganizationDTO.from_db(organization)
