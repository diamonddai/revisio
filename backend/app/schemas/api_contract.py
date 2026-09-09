from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentCategory = Literal["Amplifier", "Analyst", "Bridger", "Adverser"]
OffsetLevel = Literal["none", "minor", "sig", "major"]
NodeType = Literal[
    "neutral",
    "authority",
    "amplifier",
    "analyst",
    "bridger",
    "adverser",
    "anxiety",
    "mobilizer",
]
class UploadResponse(BaseModel):
    url: str | None = None
    dataUrl: str | None = None


class UploadCaseResponse(BaseModel):
    caseRef: str | None = None
    chartSpecRef: str | None = None
    metadataRef: str | None = None
    dataRef: str | None = None
    imageRef: str | None = None


class AgentProfile(BaseModel):
    role: str
    institution: str | None = None


class SimulationStartRequest(BaseModel):
    agentCount: int = Field(ge=0, le=6)
    agentCategories: list[AgentCategory] = Field(min_length=1)
    agentProfiles: list[AgentProfile] | None = None
    maxDepth: int | None = Field(default=None, ge=1, le=6)
    mode: str | None = None  # legacy compatibility field, no longer primary control input
    description: str | None = None
    topic: str | None = None
    imageRef: str | None = None
    caseRef: str | None = None
    chartSpecRef: str | None = None
    metadataRef: str | None = None


class TreeNode(BaseModel):
    id: str
    label: str
    actionLabel: str | None = None
    nodeType: NodeType
    platform: str | None = None  # legacy field, UI currently uses institution instead
    role: str | None = None
    institution: str | None = None
    motivation: str | None = None
    offset: OffsetLevel | None = None
    imageUrl: str | None = None
    chartSpecUrl: str | None = None
    chartSpec: dict | None = None
    operations: list[str] | None = None
    variantDescription: str | None = None
    layers: str | None = None


class TreeEdge(BaseModel):
    id: str
    source: str
    target: str
    offset: OffsetLevel | None = None


class TreePayload(BaseModel):
    nodes: list[TreeNode]
    edges: list[TreeEdge]
    nodeCount: int
    edgeCount: int
    maxDepth: int
    highestOffsetPath: str
    topologyType: str


class AgentLogItem(BaseModel):
    id: str
    time: str
    source: str
    message: str
    offsetLevel: OffsetLevel | None = None


class SummaryPayload(BaseModel):
    agentCount: int
    edgeCount: int
    highestOffset: OffsetLevel


class PathOffsetTrendItem(BaseModel):
    step: str
    offset: OffsetLevel


class SimulationStartResponse(BaseModel):
    ok: bool
    taskId: str | None = None
    tree: TreePayload | None = None
    agentLog: list[AgentLogItem] | None = None
    summary: SummaryPayload | None = None
    pathOffsetTrend: list[PathOffsetTrendItem] | None = None
    overallVariantDescription: str | None = None
    variantImageUrl: str | None = None

