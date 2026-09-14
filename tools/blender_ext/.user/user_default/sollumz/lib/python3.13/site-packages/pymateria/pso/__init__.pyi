import pymateria
import pymateria.rsc7


class Serializer:
    @property
    def rsc7(self) -> pymateria.rsc7.Serializer:
        """First pass RSC7 serializer."""

    @property
    def final_rsc7(self) -> pymateria.rsc7.Serializer:
        """Final pass RSC7 serializer."""

    @property
    def messages(self) -> pymateria.DiagnosticMessages: ...

    @property
    def metadata(self) -> pymateria.UserMetadata: ...

    @property
    def non_final_hash_strings(self) -> list[str]: ...

    @property
    def final_hash_strings(self) -> list[str]: ...

    @property
    def encrypted_strings(self) -> bool: ...

    @property
    def target(self) -> pymateria.AssetTarget: ...

class Deserializer:
    @property
    def rsc7(self) -> pymateria.rsc7.Deserializer: ...

    @property
    def messages(self) -> pymateria.DiagnosticMessages: ...

    @property
    def strings_encrypted(self) -> bool:
        """True if final strings were encrypted in the PSO file."""

    @property
    def non_final_hash_strings(self) -> list[str]: ...

    @property
    def final_hash_strings(self) -> list[str]: ...

    def lookup_string(self, hash: int) -> str | None:
        """
        Resolve a hash to its string from the PSO string tables, or None if not found.
        """

    @property
    def target(self) -> pymateria.AssetTarget: ...
