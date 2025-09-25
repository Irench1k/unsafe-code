from pydantic import BaseModel, ConfigDict, EmailStr

from ..models import Organization as OrganizationModel


class CreateOrganization(BaseModel):
    name: str
    domain: str
    owner_email: EmailStr
    model_config = ConfigDict(extra='forbid')

class RegisterOrganizationRequest(BaseModel):
    """Schema for organization registration with owner user creation"""
    org_name: str
    domain: str
    owner_email: EmailStr
    owner_first_name: str
    owner_last_name: str
    owner_password: str
    model_config = ConfigDict(extra='forbid')

class OrganizationDTO(BaseModel):
    name: str
    domain: str
    owner_email: EmailStr
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, organization: OrganizationModel):
        return cls(name=organization.name, domain=organization.domain, owner_email=organization.owner_email)
