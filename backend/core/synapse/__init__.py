"""Synapse (Plugin) module"""
from .synapse import (
    Synapse,
    SynapseStatus,
    create_web_search_synapse,
    create_file_read_synapse,
    create_medical_terminology_synapse
)

__all__ = [
    "Synapse",
    "SynapseStatus",
    "create_web_search_synapse",
    "create_file_read_synapse",
    "create_medical_terminology_synapse"
]
