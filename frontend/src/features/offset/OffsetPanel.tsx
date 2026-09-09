import { useMemo, useState, useEffect } from "react";
import { useSimulation } from "../../context/simulation";
import type { AgentNode } from "../../types/contracts";
import { ROLE_COLORS, AGENT_PROFILE_COLORS } from "../../constants/agentProfile";
import type { RoleKey } from "../../constants/codebook";
import robotIcon from "../../assets/icon/robot.png";

/** 过程流节点颜色：与左侧 Agent 池完全一致，优先 role 再 nodeType，nodeType 映射与 agentProfile 对齐 */
const NODE_TYPE_COLOR: Record<string, string> = {
  publisher: AGENT_PROFILE_COLORS[0],
  analyst: AGENT_PROFILE_COLORS[0],
  bridger: AGENT_PROFILE_COLORS[1],
  adverser: AGENT_PROFILE_COLORS[2],
  amplifier: AGENT_PROFILE_COLORS[3],
  extender: AGENT_PROFILE_COLORS[4],
  authority: AGENT_PROFILE_COLORS[1],
  neutral: "#8c8c8c",
  anxiety: AGENT_PROFILE_COLORS[3],
  mobilizer: AGENT_PROFILE_COLORS[4],
};
function getProcessNodeColor(node: AgentNode): string {
  if (node.id === "SRC") return AGENT_PROFILE_COLORS[1];
  if (node.role && node.role in ROLE_COLORS) return ROLE_COLORS[node.role as RoleKey];
  const key = (node.nodeType ?? "").toLowerCase();
  return NODE_TYPE_COLOR[key] ?? "#8c8c8c";
}

/** 过程流显示的角色名：第一个（SRC）为 Bridger，其余为 codebook 角色名或由 nodeType 映射，不再使用 Publisher */
const NODE_TYPE_TO_ROLE_LABEL: Record<string, string> = {
  publisher: "Bridger",
  analyst: "Analyst",
  bridger: "Bridger",
  adverser: "Adverser",
  amplifier: "Amplifier",
  extender: "Extender",
  authority: "Bridger",
  neutral: "Bridger",
  anxiety: "Amplifier",
  mobilizer: "Extender",
};
function getProcessRoleLabel(node: AgentNode, isFirst: boolean): string {
  if (isFirst) return "Bridger";
  if (node.role && (node.role === "Bridger" || node.role === "Extender" || node.role === "Adverser" || node.role === "Amplifier"))
    return node.role;
  const key = (node.nodeType ?? "").toLowerCase();
  return NODE_TYPE_TO_ROLE_LABEL[key] ?? "Bridger";
}

/** 右侧偏移分析面板：预览 + 过程流两块，统一左对齐、同一边距 */
const RIGHT_PANEL_PADDING = 8;

const OFFSET_PANEL = {
  /** 顶部留足空间，避免 previewSectionMarginTop 负值导致“预览”被父级 overflow 裁切 */
  bodyPaddingTop: 20,
  bodyPaddingH: 0,
  bodyPaddingBottom: 8,
  /** 整块预览区域（标题+框）相对面板上移的像素，负值上移 */
  previewSectionMarginTop: -18,
  /** “预览”标题 */
  previewLabelFontSize: 14,
  previewLabelFontWeight: 700 as const,
  previewLabelColor: "#3D4450",
  previewLabelMarginBottom: 8,
  previewBoxMinHeight: 180,
  previewBoxMaxHeight: 320,
  previewBoxRadius: 8,
  /** 预览框内部背景色 */
  previewBoxBg: "#F4F5F7",
  /** 内嵌边框：BDC9D1，inside，dashed 2，weight 1 */
  previewBoxInsetBorder: "1px dashed #BDC9D1",
  previewBoxOutlineOffset: -1,
  previewPlaceholderColor: "#808993",
  previewPlaceholderFontSize: 12,
} as const;

/** panel3 风格常量：三块之间明显留白，三框宽度平齐、内部分别配色 */
const STYLE = {
  /** 三个部分之间的留白间隙 */
  sectionGap: 24,
  /** 三框统一左侧留白，保证宽度平齐 */
  sectionPaddingLeft: 8,
  /** 区块外框（预览框、过程框） */
  blockBorder: "1px solid #E0E2E5",
  blockRadius: 8,
  blockPadding: 16,
  /** 过程框内部背景色 */
  processBoxBg: "#F9FAFA",
  /** 过程框内嵌边框：BDC9D1，solid，weight 1 */
  processBoxInsetBorder: "1px solid #BDC9D1",
  processBoxInsetBorderOffset: -1,
  sectionTitle: { color: "#333", fontWeight: 600, fontSize: 14, marginBottom: 8 },
  boxBorder: "1px solid #e0e0e0",
  boxRadius: 8,
  processIconSize: 24,
  processLineColor: "#d9d9d9",
  processDashedColor: "#e8e8e8",
  tagBg: "#f5f5f5",
  tagBorder: "1px solid #d9d9d9",
  tagDashedBorder: "1px dashed #d9d9d9",
  descColor: "#595959",
  descFontSize: 12,
  /** 过程框高度：拉长底部，增大显示区域，减少与面板底端距离 */
  processBoxMinHeight: 280,
  processBoxMaxHeight: 560,
  processBoxPaddingTop: 12,
  processBoxPaddingRight: 8,
  processBoxPaddingBottom: 8,
  processBoxPaddingLeft: 12,
  /** 过程框内 icon 间连线：C1CBD1，dashed 5，weight 2 */
  processConnectorLineColor: "#C1CBD1",
  processConnectorLineWidth: 2,
  processConnectorDashLength: 5,
} as const;

/** 将 operations 按 DATA / TEXT / VISUAL 分组，其余归为 None */
function groupOperationsByLayer(ops: string[]): {
  data: string[];
  text: string[];
  visual: string[];
  none: string[];
} {
  const data: string[] = [];
  const text: string[] = [];
  const visual: string[] = [];
  const none: string[] = [];
  for (const op of ops) {
    const upper = op.toUpperCase();
    if (upper.startsWith("DATA")) data.push(op.replace(/^data\s*:?\s*/i, "").trim() || op);
    else if (upper.startsWith("TEXT")) text.push(op.replace(/^text\s*:?\s*/i, "").trim() || op);
    else if (upper.startsWith("VISUAL")) visual.push(op.replace(/^visual\s*:?\s*/i, "").trim() || op);
    else none.push(op);
  }
  return { data, text, visual, none };
}

/** 从根到当前节点的路径 */
function getPathFromRoot(
  nodes: AgentNode[],
  edges: { source: string; target: string }[],
  toNodeId: string
): AgentNode[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const parentOf = new Map<string, string>();
  for (const e of edges) parentOf.set(e.target, e.source);
  const path: AgentNode[] = [];
  let id: string | undefined = toNodeId;
  while (id) {
    const node = byId.get(id);
    if (node) path.unshift(node);
    id = parentOf.get(id);
  }
  return path;
}

export default function OffsetPanel() {
  const {
    selectedNode,
    variantImageUrl,
    tree,
  } = useSimulation();

  const isNodeView = selectedNode != null;

  const displayVariantImageUrl = isNodeView
    ? (selectedNode.imageUrl ?? variantImageUrl)
    : variantImageUrl;
  const [previewAspectRatio, setPreviewAspectRatio] = useState<number | null>(null);

  useEffect(() => {
    setPreviewAspectRatio(null);
  }, [displayVariantImageUrl]);

  const pathToSelected = useMemo(() => {
    if (!tree || !selectedNode) return [];
    return getPathFromRoot(tree.nodes, tree.edges, selectedNode.id);
  }, [tree, selectedNode]);

  const processContent = useMemo(() => {
    if (!tree) {
      return (
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#8c8c8c",
            fontSize: STYLE.descFontSize,
          }}
        >
          Process will appear here after simulation
        </div>
      );
    }
    if (pathToSelected.length > 0) {
      return (
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            overflowX: "hidden",
            paddingRight: 4,
          }}
        >
          <ProcessTimeline path={pathToSelected} />
        </div>
      );
    }
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: STYLE.descFontSize,
          color: "#8c8c8c",
          textAlign: "center",
          padding: 16,
        }}
      >
        Click a propagation tree node to see agents and operations (DATA / TEXT / Visual) along the path
      </div>
    );
  }, [tree, pathToSelected]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: STYLE.sectionGap,
        width: "100%",
        flex: 1,
        minHeight: 0,
        overflowX: "visible",
        overflowY: "auto",
        paddingTop: OFFSET_PANEL.bodyPaddingTop,
        paddingLeft: RIGHT_PANEL_PADDING,
        paddingRight: RIGHT_PANEL_PADDING,
        paddingBottom: OFFSET_PANEL.bodyPaddingBottom,
      }}
    >
        {/* 预览：bodyPaddingTop 足够时负 margin 不会导致“预览”被父级裁切 */}
        <div style={{ flexShrink: 0, overflow: "visible", marginTop: OFFSET_PANEL.previewSectionMarginTop }}>
          <div
            style={{
              marginBottom: OFFSET_PANEL.previewLabelMarginBottom,
              fontSize: OFFSET_PANEL.previewLabelFontSize,
              fontWeight: OFFSET_PANEL.previewLabelFontWeight,
              color: OFFSET_PANEL.previewLabelColor,
              lineHeight: 1.4,
              paddingTop: 2,
              minHeight: 20,
            }}
          >
            Preview
          </div>
          <div
            style={{
              width: "100%",
              minHeight: OFFSET_PANEL.previewBoxMinHeight,
              maxHeight: OFFSET_PANEL.previewBoxMaxHeight,
              height: displayVariantImageUrl ? undefined : OFFSET_PANEL.previewBoxMinHeight,
              aspectRatio: displayVariantImageUrl && previewAspectRatio ? `${previewAspectRatio}` : undefined,
              borderRadius: OFFSET_PANEL.previewBoxRadius,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: OFFSET_PANEL.previewBoxBg,
              outline: OFFSET_PANEL.previewBoxInsetBorder,
              outlineOffset: OFFSET_PANEL.previewBoxOutlineOffset,
              overflow: "hidden",
            }}
          >
            {displayVariantImageUrl ? (
              <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <img
                  src={displayVariantImageUrl}
                  alt="Variant preview"
                  onLoad={(e) => {
                    const img = e.currentTarget;
                    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
                      setPreviewAspectRatio(img.naturalWidth / img.naturalHeight);
                    }
                  }}
                  style={{ maxWidth: "100%", maxHeight: "100%", width: "100%", height: "100%", objectFit: "contain" }}
                />
              </div>
            ) : (
              <span
                style={{
                  color: OFFSET_PANEL.previewPlaceholderColor,
                  fontSize: OFFSET_PANEL.previewPlaceholderFontSize,
                }}
              >
                {isNodeView ? "No variant for this node" : "Click a node to view variant preview"}
              </span>
            )}
          </div>
        </div>

        {/* 过程流 */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", marginTop: -18 }}>
          <div style={{ ...STYLE.sectionTitle, flexShrink: 0 }}>Process</div>
          <div
            style={{
              flex: 1,
              minHeight: STYLE.processBoxMinHeight,
              maxHeight: STYLE.processBoxMaxHeight,
              borderRadius: STYLE.blockRadius,
              background: STYLE.processBoxBg,
              outline: STYLE.processBoxInsetBorder,
              outlineOffset: STYLE.processBoxInsetBorderOffset,
              paddingTop: STYLE.processBoxPaddingTop,
              paddingRight: STYLE.processBoxPaddingRight,
              paddingBottom: STYLE.processBoxPaddingBottom,
              paddingLeft: STYLE.processBoxPaddingLeft,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {processContent}
          </div>
        </div>
    </div>
  );
}

/** 实心倒三角：Polygon #464647，W6 H4，靠右下方；展开向下，收起向右 */
const CHEVRON_COLOR = "#464647";
const CHEVRON_W = 6;
const CHEVRON_H = 4;
function SolidChevron({ expanded }: { expanded: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 0,
        height: 0,
        borderLeft: `${CHEVRON_W / 2}px solid transparent`,
        borderRight: `${CHEVRON_W / 2}px solid transparent`,
        borderTop: `${CHEVRON_H}px solid ${CHEVRON_COLOR}`,
        transition: "transform 0.2s",
        transform: expanded ? "rotate(0deg)" : "rotate(-90deg)",
      }}
    />
  );
}

/** 过程时间线：左侧彩色 robot 图标 + 贯穿每块的虚线；首节点（Bridger）无操作框；其余角色可下拉展开/收起 */
const PROCESS_AGENT_GAP = 20; // 角色与角色之间统一间距
const PROCESS_ICON_TO_PANEL_GAP = 10; // 图标行与操作面板之间间距

function ProcessTimeline({ path }: { path: AgentNode[] }) {
  const iconSize = 28;
  const lineLeft = iconSize / 2;
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setExpanded({});
  }, [path]);

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div style={{ position: "relative", paddingLeft: 2, paddingBottom: 8 }}>
      {path.map((node, idx) => {
        const ops = node.operations ?? [];
        const { data: dataOps, text: textOps, visual: visualOps } = groupOperationsByLayer(ops);
        const dotColor = getProcessNodeColor(node);
        const isFirst = idx === 0;
        const roleLabel = getProcessRoleLabel(node, isFirst);
        const isExpanded = expanded[node.id] !== false;

        return (
          <div key={node.id} style={{ position: "relative", marginBottom: PROCESS_AGENT_GAP }}>
            {/* 虚线：C1CBD1 dashed 5 weight 2，从本块顶部贯穿到下一块顶部 */}
            <div
              style={{
                position: "absolute",
                left: lineLeft,
                top: 0,
                bottom: idx < path.length - 1 ? -PROCESS_AGENT_GAP : 0,
                width: STYLE.processConnectorLineWidth,
                background: `repeating-linear-gradient(to bottom, ${STYLE.processConnectorLineColor} 0, ${STYLE.processConnectorLineColor} ${STYLE.processConnectorDashLength}px, transparent ${STYLE.processConnectorDashLength}px, transparent ${STYLE.processConnectorDashLength * 2}px)`,
                pointerEvents: "none",
              }}
            />

            {/* 左侧彩色 robot 图标 + 角色名 + 实心倒三角（首节点为 Bridger 无操作框，其余点击展开/收起） */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: !isFirst && isExpanded ? PROCESS_ICON_TO_PANEL_GAP : 0,
                position: "relative",
                zIndex: 1,
              }}
            >
              <div
                style={{
                  width: iconSize,
                  height: iconSize,
                  borderRadius: "50%",
                  background: dotColor,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <img src={robotIcon} alt="" style={{ width: 16, height: 16, objectFit: "contain" }} />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 6, flex: 1, minWidth: 0 }}>
                <span style={{ fontWeight: 600, color: "#6C6C6E", fontSize: 14, lineHeight: 1 }}>
                  {roleLabel}
                </span>
                {!isFirst && node.institution && (
                  <span
                    style={{
                      fontSize: 11,
                      color: "#8B95A1",
                      lineHeight: 1.1,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      maxWidth: 180,
                    }}
                    title={node.institution}
                  >
                    @{node.institution}
                  </span>
                )}
                {!isFirst && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={() => toggleExpanded(node.id)}
                    onKeyDown={(e) => e.key === "Enter" && toggleExpanded(node.id)}
                    style={{ display: "inline-flex", cursor: "pointer", flexShrink: 0, marginBottom: 2 }}
                  >
                    <SolidChevron expanded={isExpanded} />
                  </span>
                )}
              </div>
            </div>

            {/* 首节点（Bridger）无操作框；其余角色：可折叠的 DATA / TEXT / Visual 三块，无外层大框，三个白色小框 */}
            {!isFirst && isExpanded && (
              <div
                style={{
                  marginLeft: iconSize + 6,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  position: "relative",
                  zIndex: 1,
                }}
              >
                <Block label="DATA" layer="DATA">
                  {dataOps.length > 0 ? dataOps.join("; ") : "None"}
                </Block>
                <Block label="TEXT" layer="TEXT">
                  {textOps.length > 0 ? textOps.join("; ") : "None"}
                </Block>
                <Block label="Visual" layer="VISUAL">
                  {visualOps.length > 0 ? visualOps.join("; ") : "None"}
                </Block>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** 过程框内三个小框：白底，圆角 14，随内容灵活伸缩；用 border 才能与 borderRadius 一起生效 */
const PROCESS_BLOCK_BORDER = "1px solid #DFE9EF";
const PROCESS_BLOCK_RADIUS = 14;

/** DATA: dashed 5 weight 3, VISUAL: dashed 2 weight 5；用 SVG 描边才能区分 dash 长度 */
const LABEL_BOX_WIDTH = 55;
const LABEL_BOX_HEIGHT = 23;
const LABEL_BOX_RADIUS = 14;
function makeDashedBorderSvg(dashArray: string, strokeWidth: number): string {
  const x = strokeWidth / 2;
  const y = strokeWidth / 2;
  const w = LABEL_BOX_WIDTH - strokeWidth;
  const h = LABEL_BOX_HEIGHT - strokeWidth;
  const rx = LABEL_BOX_RADIUS - strokeWidth / 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${LABEL_BOX_WIDTH}" height="${LABEL_BOX_HEIGHT}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" ry="${rx}" fill="none" stroke="#C2C2C2" stroke-width="${strokeWidth}" stroke-dasharray="${dashArray}"/></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}
const LABEL_BOX_BG = {
  DATA: makeDashedBorderSvg("5 3", 3),
  VISUAL: makeDashedBorderSvg("2 2", 5),
} as const;
const LABEL_BOX_STYLE = {
  DATA: { backgroundImage: LABEL_BOX_BG.DATA, backgroundSize: "100% 100%", backgroundRepeat: "no-repeat", border: "none", boxSizing: "border-box" as const },
  TEXT: { border: "3px solid #C2C2C2", boxSizing: "border-box" as const },
  VISUAL: { backgroundImage: LABEL_BOX_BG.VISUAL, backgroundSize: "100% 100%", backgroundRepeat: "no-repeat", border: "none", boxSizing: "border-box" as const },
};

/** 单个层面小框：白底，内嵌 DFE9EF 线；DATA/TEXT/VISUAL 字样 Arial Bold，外围框 C2C2C2 按层区分，框内白色 */
function Block({
  label,
  layer,
  children,
}: {
  label: string;
  layer: "DATA" | "TEXT" | "VISUAL";
  children: string;
}) {
  const labelBoxStyle = LABEL_BOX_STYLE[layer];
  return (
    <div
      style={{
        background: "#fff",
        border: PROCESS_BLOCK_BORDER,
        boxSizing: "border-box",
        borderRadius: PROCESS_BLOCK_RADIUS,
        padding: 10,
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: LABEL_BOX_WIDTH,
          height: LABEL_BOX_HEIGHT,
          borderRadius: LABEL_BOX_RADIUS,
          background: "#fff",
          ...labelBoxStyle,
          fontFamily: "Arial",
          fontWeight: "bold",
          fontSize: 12,
          color: "#808993",
          marginBottom: 4,
        }}
      >
        {label}
      </span>
      <div
        style={{
          fontSize: 12,
          color: "#7F8994",
          lineHeight: 1.5,
        }}
      >
        {children}
      </div>
    </div>
  );
}
