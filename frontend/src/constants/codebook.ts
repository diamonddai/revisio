/**
 * 与 docs/codebook.md 一致：角色、平台（机构）、框架操作层级
 */

/** 角色类型（编码指南 一） */
export const ROLES = [
  { value: "Bridger", label: "Bridger" },
  { value: "Extender", label: "Extender" },
  { value: "Adverser", label: "Adverser" },
  { value: "Amplifier", label: "Amplifier" },
] as const;

export type RoleKey = (typeof ROLES)[number]["value"];

/** 角色功能介绍（与 codebook 核心功能一致，用于 Agent 池与设置面板展示） */
export const ROLE_DESCRIPTIONS: Record<RoleKey, string> = {
  Bridger: "Connecting data with the public",
  Extender: "Extends issues to related domains",
  Adverser: "Builds counter-framing",
  Amplifier: "Reinforces existing narrative",
};

/** 平台/机构（编码指南 二） */
export const INSTITUTIONS = [
  "Third-party data platform",
  "Personal site / blog",
  "Research institution",
  "Online community / UGC",
  "Social media",
  "News media",
  "Government / IGO",
  "Institutional blog",
] as const;

export type InstitutionKey = (typeof INSTITUTIONS)[number];

/** 单个 Agent 配置（仅 role + institution，无 motivation） */
export interface AgentProfileEntry {
  role: RoleKey | null;
  institution: string | null;
}

/** 框架操作层级（编码指南 三）：用于边线样式与过程展示 */
export const FRAME_LAYERS = ["DATA", "TEXT", "VISUAL"] as const;
export type FrameLayer = (typeof FRAME_LAYERS)[number];
