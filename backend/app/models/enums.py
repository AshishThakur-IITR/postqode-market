import enum


class UserRole(str, enum.Enum):
    """Platform-level user roles."""
    SUPER_ADMIN = "super_admin"   # Marketplace owner, approves everything
    ORG_ADMIN = "org_admin"       # Organization admin after subscription
    ORG_USER = "org_user"         # Regular org member
    PUBLISHER = "publisher"       # Can publish agents


class SubscriptionPlan(str, enum.Enum):
    """Marketplace subscription plans."""
    NONE = "none"
    STARTER = "starter"           # $9.99/mo
    PROFESSIONAL = "professional" # $49.99/mo
    ENTERPRISE = "enterprise"     # $199.99/mo


class SubscriptionStatus(str, enum.Enum):
    """Organization subscription status."""
    NONE = "none"
    PENDING = "pending"   # Awaiting super admin approval
    ACTIVE = "active"     # Active subscription
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class AgentStatus(str, enum.Enum):
    """Agent publishing lifecycle states."""
    DRAFT = "draft"                    # Initial state, editable by publisher
    PENDING_REVIEW = "pending_review"  # Submitted for admin review
    APPROVED = "approved"              # Passed review, ready to publish
    REJECTED = "rejected"              # Failed review, can be edited and resubmitted
    PUBLISHED = "published"            # Live in marketplace
    ARCHIVED = "archived"              # Removed from marketplace


class DeploymentType(str, enum.Enum):
    """Types of agent deployment environments."""
    CLOUD_MANAGED = "cloud_managed"    # PostQode managed cloud
    KUBERNETES = "kubernetes"          # Customer's K8s cluster
    VM_STANDALONE = "vm_standalone"    # Standalone VM/bare metal
    SERVERLESS = "serverless"          # Lambda/Azure Functions
    EDGE = "edge"                      # Edge devices
    DOCKER = "docker"                  # Docker container


class DeploymentStatus(str, enum.Enum):
    """Status of an agent deployment."""
    PENDING = "pending"       # Deployment in progress
    ACTIVE = "active"         # Running successfully
    STOPPED = "stopped"       # Manually stopped
    ERROR = "error"           # Deployment failed
    UPDATING = "updating"     # Being updated
