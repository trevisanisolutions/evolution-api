import time
from dataclasses import dataclass


@dataclass
class UserBufferDTO:
    replica_id: str
    replica_id_last_updated: int
    messages: list
    last_updated: int
    instance_name: str
    presence: str = "available"
    presence_last_updated: int = 0

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            replica_id=data.get("replica_id", ""),
            replica_id_last_updated=int(data.get("replica_id_last_updated", 0)),
            messages=data.get("messages", []),
            last_updated=int(time.time()),
            instance_name=data.get("instance_name", ""),
            presence="available",
            presence_last_updated=data.get("presence_last_updated", 0)
        )
