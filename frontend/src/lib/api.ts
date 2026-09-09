import axios from "axios";
import type {
  AgentCategory,
  PropagationTree,
  AgentLogEntry,
  SimulationResultSummary,
  PathOffsetPoint,
} from "../types/contracts";

const baseURL = import.meta.env.VITE_API_BASE ?? "/api";
const timeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 30000);

export const api = axios.create({
  baseURL,
  timeout: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 30000,
  headers: { "Content-Type": "application/json" },
});

/** 上传完整案例（chart_spec + metadata），与模拟数据集一致；返回 caseRef 供开始模拟使用 */
export interface UploadCaseParams {
  chart_spec: File;
  metadata: File;
  data?: File;
  image?: File;
}
export interface UploadCaseResult {
  caseRef?: string;
  chartSpecRef?: string;
  metadataRef?: string;
  dataRef?: string;
  imageRef?: string;
}
export async function uploadCase(files: UploadCaseParams): Promise<UploadCaseResult> {
  const form = new FormData();
  form.append("chart_spec", files.chart_spec);
  form.append("metadata", files.metadata);
  if (files.data) form.append("data", files.data);
  if (files.image) form.append("image", files.image);
  const { data } = await api.post<UploadCaseResult>("/upload-case", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** 上传原始可视化（已废弃不作为模拟输入，仅保留接口名供兼容） */
export async function uploadVisualization(file: File): Promise<{ url?: string; dataUrl?: string }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<{ url?: string; dataUrl?: string }>("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** 开始模拟响应：同步时带 tree/agentLog 等，异步时仅 ok + taskId。中间面板（传播树 + AGENT LOG）仅由此结果驱动，无需其他接口。 */
export interface StartSimulationResult {
  ok: boolean;
  taskId?: string;
  tree?: PropagationTree;
  agentLog?: AgentLogEntry[];
  summary?: SimulationResultSummary;
  pathOffsetTrend?: PathOffsetPoint[];
  overallVariantDescription?: string;
  variantImageUrl?: string;
}

/** 开始模拟：必传 caseRef；maxDepth、agentProfiles（每个 agent 的 role+institution） */
/** 与接口文档 § 2.2 一致：不含 topic（文档未列该字段） */
export async function startSimulation(params: {
  agentCount: number;
  agentCategories: AgentCategory[];
  agentProfiles?: { role: string; institution: string }[];
  maxDepth?: number;
  description?: string;
  caseRef?: string;
  chartSpecRef?: string;
  metadataRef?: string;
  imageRef?: string;
}): Promise<StartSimulationResult> {
  // 模拟可能耗时很长（多 agent 多 depth），单独设 15 分钟超时，不受全局限制
  const { data } = await api.post<StartSimulationResult>(
    "/simulation/start",
    params,
    { timeout: 900_000 }
  );
  return data;
}

/** 健康检查 */
export async function ping(): Promise<{ ok: boolean }> {
  const res = await api.get("/health");
  return { ok: (res.data as { ok?: boolean })?.ok === true };
}
