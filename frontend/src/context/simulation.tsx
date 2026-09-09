import React, { createContext, useContext, useState, useCallback } from "react";
import type {
  UploadPreview,
  PlatformKey,
  AgentCategory,
  PropagationTree,
  AgentLogEntry,
  AgentNode,
  PathOffsetPoint,
  SimulationStatus,
  SimulationResultSummary,
} from "../types/contracts";
import type { AgentProfileEntry } from "../constants/codebook";

interface SimulationContextValue {
  // 左侧：上传与设置
  preview: UploadPreview | null;
  setPreview: React.Dispatch<React.SetStateAction<UploadPreview | null>>;
  caseRef: string | null;
  setCaseRef: (v: string | null) => void;
  agentCount: number;
  setAgentCount: (n: number) => void;
  maxDepth: number;
  setMaxDepth: (n: number) => void;
  platforms: PlatformKey[];
  setPlatforms: (p: PlatformKey[]) => void;
  agentCategories: AgentCategory[];
  setAgentCategories: (c: AgentCategory[]) => void;
  /** 每个 Agent 的 profile（仅 role + institution），长度与 agentCount 一致 */
  agentProfiles: AgentProfileEntry[];
  setAgentProfiles: (p: AgentProfileEntry[] | ((prev: AgentProfileEntry[]) => AgentProfileEntry[])) => void;
  description: string;
  setDescription: (s: string) => void;

  // 模拟状态
  status: SimulationStatus;
  setStatus: (s: SimulationStatus) => void;
  summary: SimulationResultSummary | null;
  setSummary: (s: SimulationResultSummary | null) => void;

  // 中间：传播树与 Log
  tree: PropagationTree | null;
  setTree: (t: PropagationTree | null) => void;
  agentLog: AgentLogEntry[];
  setAgentLog: (log: AgentLogEntry[] | ((prev: AgentLogEntry[]) => AgentLogEntry[])) => void;
  appendLog: (entry: Omit<AgentLogEntry, "id">) => void;

  // 选中节点（用于右侧偏移分析）
  selectedNode: AgentNode | null;
  setSelectedNode: (n: AgentNode | null) => void;

  // 右侧：整体或单节点 的 变体描述、路径偏移
  overallVariantDescription: string;
  setOverallVariantDescription: (s: string) => void;
  pathOffsetTrend: PathOffsetPoint[];
  setPathOffsetTrend: (p: PathOffsetPoint[]) => void;
  // 当前展示的图片：原始 / 最终变体 或 节点变体
  originalImageUrl: string | null;
  variantImageUrl: string | null;
  setOriginalImageUrl: (s: string | null) => void;
  setVariantImageUrl: (s: string | null) => void;
}

const SimulationContext = createContext<SimulationContextValue | undefined>(undefined);

export function SimulationProvider({ children }: { children: React.ReactNode }) {
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [caseRef, setCaseRef] = useState<string | null>(null);
  const [agentCount, setAgentCount] = useState(5);
  const [maxDepth, setMaxDepth] = useState(4);
  const [platforms, setPlatforms] = useState<PlatformKey[]>(["longform", "shortform"]);
  const [agentProfiles, setAgentProfiles] = useState<AgentProfileEntry[]>(() =>
    Array.from({ length: 5 }, () => ({ role: null, institution: null }))
  );
  const [agentCategories, setAgentCategories] = useState<AgentCategory[]>(["Bridger"]);
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<SimulationStatus>("idle");
  const [summary, setSummary] = useState<SimulationResultSummary | null>(null);
  const [tree, setTree] = useState<PropagationTree | null>(null);
  const [agentLog, setAgentLog] = useState<AgentLogEntry[]>([]);
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const [overallVariantDescription, setOverallVariantDescription] = useState("");
  const [pathOffsetTrend, setPathOffsetTrend] = useState<PathOffsetPoint[]>([]);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  const [variantImageUrl, setVariantImageUrl] = useState<string | null>(null);

  const appendLog = useCallback((entry: Omit<AgentLogEntry, "id">) => {
    setAgentLog((prev) => [
      ...prev,
      { ...entry, id: `log-${Date.now()}-${prev.length}` },
    ]);
  }, []);

  const value: SimulationContextValue = {
    preview,
    setPreview,
    caseRef,
    setCaseRef,
    agentCount,
    setAgentCount,
    maxDepth,
    setMaxDepth,
    platforms,
    setPlatforms,
    agentCategories,
    setAgentCategories,
    agentProfiles,
    setAgentProfiles,
    description,
    setDescription,
    status,
    setStatus,
    summary,
    setSummary,
    tree,
    setTree,
    agentLog,
    setAgentLog,
    appendLog,
    selectedNode,
    setSelectedNode,
    overallVariantDescription,
    setOverallVariantDescription,
    pathOffsetTrend,
    setPathOffsetTrend,
    originalImageUrl,
    variantImageUrl,
    setOriginalImageUrl,
    setVariantImageUrl,
  };

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const ctx = useContext(SimulationContext);
  if (!ctx) throw new Error("useSimulation must be used within SimulationProvider");
  return ctx;
}
