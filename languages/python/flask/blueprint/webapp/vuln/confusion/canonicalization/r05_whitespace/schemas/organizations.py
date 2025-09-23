from pydantic import BaseModel, ConfigDict

from ..models import Organization as OrganizationModel


class CreateOrganization(BaseModel):
    name: str
    domain: str
    owner_email: str
    model_config = ConfigDict(extra='forbid')

class OrganizationDTO(BaseModel):
    name: str
    domain: str
    owner_email: str
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, organization: OrganizationModel):
        return cls(name=organization.name, domain=organization.domain, owner_email=organization.owner_email)
