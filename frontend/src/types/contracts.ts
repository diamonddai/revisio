// 主题：LLM 生成
export type TopicType =
  | "international affairs"
  | "science"
  | "politics"
  | "economy"
  | "other";

// 目标平台
export type PlatformKey = "longform" | "shortform" | "video" | "community";

// Agent 类别（与后端 API 契约一致，共四种）
export type AgentCategory = "Bridger" | "Analyst" | "Adverser" | "Amplifier";

// 节点类型（智能体画像）
export type NodeTypeKey =
  | "neutral"   // 中立/源
  | "authority"  // 权威型
  | "amplifier"  // Amplifier
  | "analyst"    // Analyst
  | "bridger"    // Bridger
  | "adverser"   // Adverser
  | "anxiety"    // 焦虑型（兼容旧数据）
  | "mobilizer"; // 动员型（兼容旧数据）

// 偏移等级
export type OffsetLevel = "none" | "minor" | "sig" | "major";

// 单条 Agent Log
export interface AgentLogEntry {
  id: string;
  time: string; // "00:00:02"
  source: "SYSTEM" | string; // 系统或 agent id
  message: string;
  offsetLevel?: OffsetLevel;
}

// 传播树节点（智能体）
export interface AgentNode {
  id: string;
  label: string;       // 显示名，如 "BBC News"
  actionLabel?: string; // 如 "新闻报道转载"
  nodeType: NodeTypeKey;
  platform?: PlatformKey;
  role?: string;       // 有则右侧展示「角色」，接口文档 § 2.3
  institution?: string; // 平台/机构，有则右侧展示；不展示 motivation
  motivation?: string; // 后端可能返回，前端不展示
  offset?: OffsetLevel;
  imageUrl?: string;
  chartSpecUrl?: string;  // 可选，该节点变体 Vega-Lite 规范 URL，接口文档 § 2.3
  chartSpec?: object;    // 可选，该节点变体 Vega-Lite 规范内联
  operations?: string[];
  variantDescription?: string;
  layers?: string;
}

// 传播树边
export interface AgentEdge {
  id: string;
  source: string;
  target: string;
  offset?: OffsetLevel;
}

// 传播树
export interface PropagationTree {
  nodes: AgentNode[];
  edges: AgentEdge[];
  nodeCount: number;
  edgeCount: number;
  maxDepth: number;
  highestOffsetPath: string; // "SRC->V2 (major)"
  topologyType: string;     // "tree"
}

// 路径偏移趋势（用于右侧图表）
export interface PathOffsetPoint {
  step: string;  // "SRC" | "V1" | "V2" ...
  offset: OffsetLevel;
}

// 上传与解读
export interface UploadPreview {
  file?: File;
  dataUrl?: string;
  description?: string;
  topic?: TopicType;
}

// 模拟状态
export type SimulationStatus = "idle" | "running" | "done" | "error";

export interface SimulationResultSummary {
  agentCount: number;
  edgeCount: number;
  highestOffset: OffsetLevel;
}
