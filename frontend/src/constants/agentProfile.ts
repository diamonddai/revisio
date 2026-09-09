import type { RoleKey } from "./codebook";

/**
 * Agent Profile 与传播树节点共用：5 种角色颜色
 * 顺序：Publisher, Bridger, Adverser, Amplifier, Extender
 */
export const AGENT_PROFILE_COLORS = [
  "#C4A64E", // Publisher / Analyst — deep gold
  "#8A8FCC", // Bridger — dusty indigo
  "#D08350", // Adverser — terracotta
  "#C44E42", // Amplifier — brick red
  "#549E9F", // Extender — muted teal
] as const;

export type AgentProfileColorIndex = 0 | 1 | 2 | 3 | 4;

/** codebook 角色 → 颜色（点亮用） */
export const ROLE_COLORS: Record<RoleKey, string> = {
  Bridger: AGENT_PROFILE_COLORS[1],
  Extender: AGENT_PROFILE_COLORS[4],
  Adverser: AGENT_PROFILE_COLORS[2],
  Amplifier: AGENT_PROFILE_COLORS[3],
};
