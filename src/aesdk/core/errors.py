"""Typed AESDK exceptions."""

from __future__ import annotations


class AESDKError(Exception):
    """Base class for SDK errors."""


class MissingPAPError(AESDKError):
    """Raised when PAP is required but missing."""


class PAPValidationError(AESDKError):
    """Raised when PAP file fails schema validation."""


class RuleEvaluationError(AESDKError):
    """Raised when a governance rule cannot be evaluated safely."""


class GovernanceBlockError(AESDKError):
    """Raised when validation status is block and execution is attempted."""


class StateTransitionError(AESDKError):
    """Raised for invalid state transitions."""


class BlobIntegrityError(AESDKError):
    """Raised when a replication blob integrity check fails."""


class BlobSignatureError(AESDKError):
    """Raised when blob signing or signature verification fails."""


class SandboxExecutionError(AESDKError):
    """Raised when sandbox code execution fails."""


class ImportWhitelistError(SandboxExecutionError):
    """Raised when code imports non-whitelisted modules."""


class ForbiddenCodePatternError(SandboxExecutionError):
    """Raised when sandbox code contains forbidden calls/patterns."""


class CitationVerificationError(AESDKError):
    """Raised on citation verification subsystem errors."""


class AttestationError(AESDKError):
    """Raised when remote attestation fails."""
