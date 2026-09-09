import { useMemo, useEffect } from "react";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import PanelCard from "../../components/PanelCard";
import { useSimulation } from "../../context/simulation";
import { AGENT_PROFILE_COLORS, ROLE_COLORS } from "../../constants/agentProfile";
import type { FrameLayer, RoleKey } from "../../constants/codebook";
import robotIcon from "../../assets/icon/robot.png";

/** panel2 风格：节点为上方彩色圆 + 下方白底圆角框（可含变体图/标签） */
const PANEL2 = {
  nodeBorder: "#DCDCDC",
  nodeBorderWidth: 1.5,
  nodeBorderRadius: 8,
  iconSize: 28,
  robotSize: 16,
  /** 圆圈相对线框上边缘的垂直偏移：负值表示向上（更靠线框上方），单位 px */
  iconOffsetTop: 18,
  /** 层数分割虚线：贯穿面板左右，与两侧边界相连 */
  dividerColor: "#9899A3",
  dividerStyle: "1px dashed #9899A3",
  edgeStroke: "#b0b0b0",
  /** 层标注菱形：W36 H31，背景 616975 50% 透明度，白字 */
  layerLabelWidth: 36,
  layerLabelHeight: 31,
  layerLabelBg: "rgba(97, 105, 117, 0.5)",
  layerLabelColor: "#ffffff",
} as const;

/** 多线时每条线在节点上的水平偏移（px）；位置 0=左、1=中、2=右；主线条(TEXT)居中，第二条在右，第三条在左 */
const HANDLE_OFFSET_PX = 9;
const POSITION_IDS = ["0", "1", "2"] as const;

/** 传播树节点：位置 handle 0/1/2 对应左/中/右，用于按规则排布 DATA/TEXT/VISUAL 多条边 */
type VariantImageNodeData = { label: string; imageUrl?: string | null; dotColor?: string };
function VariantImageNode({ data }: NodeProps<Node<VariantImageNodeData, "variantImage">>) {
  const imageUrl = data?.imageUrl ?? null;
  const dotColor = data?.dotColor ?? "#8c8c8c";
  return (
    <>
      <Handle
        id="top"
        type="target"
        position={Position.Top}
        style={{
          visibility: "hidden",
          position: "absolute",
          top: PANEL2.iconOffsetTop,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />
      {POSITION_IDS.map((posId, i) => {
        const offset = (i - 1) * HANDLE_OFFSET_PX;
        return (
          <Handle
            key={`top-${posId}`}
            id={`top-${posId}`}
            type="target"
            position={Position.Top}
            style={{
              visibility: "hidden",
              position: "absolute",
              top: PANEL2.iconOffsetTop,
              left: offset === 0 ? "50%" : `calc(50% + ${offset}px)`,
              transform: "translateX(-50%)",
            }}
          />
        );
      })}
      <div style={{ position: "relative", width: "100%", height: "100%", paddingTop: PANEL2.iconSize + 6, overflow: "visible" }}>
        {/* robot 图标 + 彩色圆：绝对定位在线框上方，通过 iconOffsetTop 调整垂直位置 */}
        <div
          style={{
            position: "absolute",
            top: PANEL2.iconOffsetTop,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 10,
            width: PANEL2.iconSize,
            height: PANEL2.iconSize,
            borderRadius: "50%",
            background: dotColor,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxSizing: "border-box",
          }}
        >
          <img src={robotIcon} alt="" style={{ width: PANEL2.robotSize, height: PANEL2.robotSize, objectFit: "contain" }} />
        </div>
        <div
          style={{
            width: "100%",
            height: "100%",
            minHeight: 90,
            borderRadius: PANEL2.nodeBorderRadius,
            border: `${PANEL2.nodeBorderWidth}px solid ${PANEL2.nodeBorder}`,
            background: "#fff",
            cursor: "pointer",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {imageUrl ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 70 }}>
              <img src={imageUrl} alt="" style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
            </div>
          ) : null}
        </div>
      </div>
      <Handle id="bottom" type="source" position={Position.Bottom} style={{ visibility: "hidden" }} />
      {POSITION_IDS.map((posId, i) => {
        const offset = (i - 1) * HANDLE_OFFSET_PX;
        return (
          <Handle
            key={`bottom-${posId}`}
            id={`bottom-${posId}`}
            type="source"
            position={Position.Bottom}
            style={{
              visibility: "hidden",
              position: "absolute",
              bottom: 0,
              left: offset === 0 ? "50%" : `calc(50% + ${offset}px)`,
              transform: "translateX(-50%)",
            }}
          />
        );
      })}
    </>
  );
}

const nodeTypes = { variantImage: VariantImageNode };

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
function getDotColorForNodeType(nodeType: string | undefined): string {
  if (!nodeType) return "#8c8c8c";
  const key = nodeType.toLowerCase();
  return NODE_TYPE_COLOR[key] ?? "#8c8c8c";
}

/** 从节点 operations 推断涉及的框架层级（DATA / TEXT / VISUAL），用于边线样式 */
function getLayersFromOperations(operations: string[] | undefined): FrameLayer[] {
  if (!operations?.length) return [];
  const layers: FrameLayer[] = [];
  for (const op of operations) {
    const u = op.toUpperCase();
    if (u.startsWith("DATA") && !layers.includes("DATA")) layers.push("DATA");
    else if (u.startsWith("TEXT") && !layers.includes("TEXT")) layers.push("TEXT");
    else if (u.startsWith("VISUAL") && !layers.includes("VISUAL")) layers.push("VISUAL");
  }
  return layers;
}

/** 三层面操作对应连线样式：DATA 密集虚线 2，TEXT solid，VISUAL 宽松虚线 4；统一 #DDDDDE weight 5 */
const EDGE_COLOR = "#DDDDDE";
const EDGE_WEIGHT = 5;
const EDGE_STYLE_BY_LAYER: Record<FrameLayer, { stroke?: string; strokeWidth?: number; strokeDasharray?: string }> = {
  DATA: { stroke: EDGE_COLOR, strokeWidth: EDGE_WEIGHT, strokeDasharray: "2 2" },
  TEXT: { stroke: EDGE_COLOR, strokeWidth: EDGE_WEIGHT },
  VISUAL: { stroke: EDGE_COLOR, strokeWidth: EDGE_WEIGHT, strokeDasharray: "4 4" },
};

const LAYER_PRIORITY: FrameLayer[] = ["DATA", "TEXT", "VISUAL"];

/** 主线条优先 TEXT；第二条在中间右侧；第三条在中间左侧。返回从左到右的层顺序，对应 handle 位置 0/1/2。 */
function getDisplayOrder(layers: FrameLayer[]): FrameLayer[] {
  if (layers.length <= 1) return layers;
  const main = layers.includes("TEXT") ? "TEXT" : layers.includes("DATA") ? "DATA" : "VISUAL";
  const others = layers.filter((l) => l !== main);
  const othersOrdered = LAYER_PRIORITY.filter((l) => others.includes(l));
  if (layers.length === 2) return [main, othersOrdered[0]];
  return [othersOrdered[1], main, othersOrdered[0]];
}

/** 层在展示顺序中的位置索引：0=左，1=中，2=右。 */
function getLayerPositionIndex(layers: FrameLayer[], layer: FrameLayer): number {
  const ordered = getDisplayOrder(layers);
  const idx = ordered.indexOf(layer);
  if (idx < 0) return 1;
  if (layers.length === 2) return idx + 1;
  return idx;
}

function buildFlowNodesAndEdges(
  tree: NonNullable<ReturnType<typeof useSimulation>["tree"]>,
  originalImageUrl: string | null
): { nodes: Node[]; edges: Edge[] } {
  const { nodes: agents, edges: rawEdges } = tree;
  const nodeWidth = 200;
  const nodeHeight = 160;
  const gapX = 80;
  const gapY = 100;

  const byId = new Map(agents.map((a) => [a.id, a]));
  const childrenOf = new Map<string, typeof agents>();
  for (const e of rawEdges) {
    if (!childrenOf.has(e.source)) childrenOf.set(e.source, []);
    const targetNode = byId.get(e.target);
    if (targetNode) childrenOf.get(e.source)!.push(targetNode);
  }

  const positions = new Map<string, { x: number; y: number }>();
  const src = agents.find((a) => a.id === "SRC") ?? agents[0];
  if (!src) return { nodes: [], edges: [] };

  positions.set(src.id, { x: 0, y: 0 });
  const queue: string[] = [src.id];
  while (queue.length > 0) {
    const id = queue.shift()!;
    const pos = positions.get(id)!;
    const kids = (childrenOf.get(id) ?? []).filter(Boolean);
    const n = kids.length;
    const childY = pos.y + nodeHeight + gapY;

    if (n === 1) {
      const childId = kids[0].id;
      positions.set(childId, { x: pos.x, y: childY });
      queue.push(childId);
    } else if (n > 1) {
      const totalW = (n - 1) * (nodeWidth + gapX);
      let childX = pos.x - totalW / 2;
      for (const k of kids) {
        positions.set(k.id, { x: childX, y: childY });
        queue.push(k.id);
        childX += nodeWidth + gapX;
      }
    }
  }

  const flowNodes: Node<VariantImageNodeData, "variantImage">[] = agents.map((a) => {
    const pos = positions.get(a.id) ?? { x: 0, y: 0 };
    const label = a.actionLabel ? `${a.label}\n${a.actionLabel}` : a.label;
    const imageUrl = a.id === "SRC" ? originalImageUrl : (a.imageUrl ?? null);
    /** 源节点 SRC 使用 Bridger 颜色；其他节点优先用 role（与左右面板保持一致），fallback nodeType */
    const dotColor =
      a.id === "SRC"
        ? AGENT_PROFILE_COLORS[1]
        : a.role && a.role in ROLE_COLORS
          ? ROLE_COLORS[a.role as RoleKey]
          : getDotColorForNodeType(a.nodeType);
    return {
      id: a.id,
      type: "variantImage",
      position: pos,
      data: { label, imageUrl, dotColor },
      style: {
        width: nodeWidth,
        height: nodeHeight,
        overflow: "visible",
      },
    };
  });

  const flowEdges: Edge[] = rawEdges.flatMap((e) => {
    const targetNode = byId.get(e.target);
    let layers = getLayersFromOperations(targetNode?.operations);
    if (e.source === "SRC" && e.target === "V2") {
      layers = layers.filter((l) => l === "DATA" || l === "TEXT");
    }
    const styleBase = { stroke: EDGE_COLOR, strokeWidth: EDGE_WEIGHT };
    const childrenCount = childrenOf.get(e.source)?.length ?? 0;
    const edgeType = childrenCount <= 1 ? "straight" : "default";
    const useCenterHandle = layers.length <= 1;
    if (layers.length === 0) {
      return [{
        source: e.source,
        target: e.target,
        type: edgeType,
        sourceHandle: "bottom",
        targetHandle: "top",
        id: e.id,
        style: styleBase,
      }];
    }
    return layers.map((layer, idx) => {
      const pos = useCenterHandle ? null : getLayerPositionIndex(layers, layer);
      return {
        source: e.source,
        target: e.target,
        type: edgeType,
        sourceHandle: useCenterHandle ? "bottom" : `bottom-${pos}`,
        targetHandle: useCenterHandle ? "top" : `top-${pos}`,
        id: layers.length > 1 ? `${e.id}-${layer}-${idx}` : e.id,
        style: { ...styleBase, ...EDGE_STYLE_BY_LAYER[layer] },
      };
    });
  });

  return { nodes: flowNodes, edges: flowEdges };
}

export default function PropagationPanel() {
  const { tree, setSelectedNode, originalImageUrl, maxDepth } = useSimulation();
  // Use the user-configured maxDepth so labels always match the input.
  // depth=1 → layerCount=2 (L0,L1). Minimum 2 layers.
  const layerCount = Math.max(2, (maxDepth ?? 1) + 1);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!tree) return { nodes: [], edges: [] };
    return buildFlowNodesAndEdges(tree, originalImageUrl ?? null);
  }, [tree, originalImageUrl]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    const agent = tree?.nodes.find((n) => n.id === node.id) ?? null;
    setSelectedNode(agent);
  };

  return (
    <PanelCard bodyStyle={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0, overflow: "hidden", paddingLeft: 0, paddingRight: 0 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1, minHeight: 0 }}>
        {/* 传播图：有树时显示底层虚线，虚线横跨面板两侧 */}
        <div style={{ flex: 1, minHeight: 380, minWidth: 0, borderRadius: "var(--radius-lg)", background: "#fff", position: "relative" }}>
          {tree && initialNodes.length > 0 ? (
            <>
              <div
                aria-hidden
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  width: "100%",
                  pointerEvents: "none",
                  zIndex: 0,
                }}
              >
                {/* Dividers: layerCount-1 lines evenly splitting the panel height */}
                {Array.from({ length: layerCount - 1 }, (_, i) => {
                  const pct = ((i + 1) / layerCount) * 100;
                  return (
                    <div
                      key={i}
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        width: "100%",
                        top: `${pct}%`,
                        height: 0,
                        borderTop: PANEL2.dividerStyle,
                      }}
                    />
                  );
                })}
                {/* Layer labels: centred vertically in each band, on the right edge */}
                {Array.from({ length: layerCount }, (_, layer) => {
                  const bandPct = 100 / layerCount;
                  const centerPct = layer * bandPct + bandPct / 2;
                  return (
                    <div
                      key={layer}
                      style={{
                        position: "absolute",
                        top: `${centerPct}%`,
                        right: 2,
                        transform: "translateY(-50%)",
                        width: PANEL2.layerLabelWidth,
                        height: PANEL2.layerLabelHeight,
                        background: PANEL2.layerLabelBg,
                        clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: PANEL2.layerLabelColor,
                        fontSize: 12,
                        fontWeight: 700,
                      }}
                    >
                      L{layer}
                    </div>
                  );
                })}
              </div>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                proOptions={{ hideAttribution: true }}
                style={{ position: "relative", zIndex: 1 }}
              >
              </ReactFlow>
            </>
          ) : null}
          {!tree || initialNodes.length === 0 ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#999",
              }}
            >
              Upload an image and click Start simulation first
            </div>
          ) : null}
        </div>
      </div>
    </PanelCard>
  );
}
