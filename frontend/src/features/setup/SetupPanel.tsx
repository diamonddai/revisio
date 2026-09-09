import { useState, useRef, useEffect } from "react";
import { Input, Slider, Button, message, Select } from "antd";
import { EditOutlined } from "@ant-design/icons";
import PanelCard from "../../components/PanelCard";
import { useSimulation } from "../../context/simulation";
import { uploadCase, startSimulation } from "../../lib/api";
import type { AgentCategory } from "../../types/contracts";
import { ROLE_COLORS } from "../../constants/agentProfile";
import { ROLES, INSTITUTIONS, ROLE_DESCRIPTIONS, type RoleKey, type AgentProfileEntry } from "../../constants/codebook";

/** 未设置时的灰色（与 Frame 26/28 一致） */
const GREY_BORDER = "#D0D3D8";
const GREY_BG = "#F5F6F8";
import robotIcon from "../../assets/icon/robot.png";
import uploadIcon from "../../assets/icon/upload.png";
import generateIcon from "../../assets/icon/generate.png";
import { panel1 } from "./panel1Styles";

const GREY_ICON = "#6B767E";
/** 仅前端演示时的虚拟 caseRef，不请求后端 */
const LOCAL_DEMO_CASE_REF = "local-demo";

/** 意图类型：用于 Auto Generate 生成以某类角色为主的 agent profile */
const INTENT_OPTIONS = [
  { value: "adverser" as const, label: "Adverse" },
  { value: "amplifier" as const, label: "Amplify" },
  { value: "extender" as const, label: "Extend" },
  { value: "bridger" as const, label: "Bridge" },
  { value: "hybrid" as const, label: "Hybrid" },
];
const ROLE_KEYS: RoleKey[] = ["Bridger", "Adverser", "Amplifier", "Extender"];

export default function SetupPanel() {
  const {
    preview,
    setPreview,
    caseRef,
    setCaseRef,
    agentCount,
    setAgentCount,
    maxDepth,
    setMaxDepth,
    agentProfiles,
    setAgentProfiles,
    agentCategories: _agentCategories,
    setAgentCategories: _setAgentCategories,
    description,
    setDescription,
    status,
    setStatus,
    summary: _summary,
    setSummary,
    setTree,
    setAgentLog,
    appendLog,
    setOriginalImageUrl,
    setVariantImageUrl,
    setOverallVariantDescription,
    setPathOffsetTrend,
    setSelectedNode,
  } = useSimulation();

  const dirInputRef = useRef<HTMLInputElement>(null);
  const [uploadingCase, setUploadingCase] = useState(false);
  /** 当前编辑的 Agent Profile 卡片索引，-1 表示未在编辑 */
  const [editingProfileIndex, setEditingProfileIndex] = useState(-1);
  /** 意图类型：点击 Auto Generate 时按此生成以某类角色为主的配置 */
  const [intentType, setIntentType] = useState<"bridger" | "adverser" | "amplifier" | "extender" | "hybrid">("hybrid");

  /** agentCount 变化时同步 agentProfiles 长度；为 0 时池为空 */
  useEffect(() => {
    const n = agentCount;
    setAgentProfiles((prev) => {
      if (prev.length === n) return prev;
      if (n === 0) return [];
      if (prev.length < n) {
        return [
          ...prev,
          ...Array.from({ length: n - prev.length }, () => ({ role: null, institution: null })),
        ];
      }
      return prev.slice(0, n);
    });
  }, [agentCount, setAgentProfiles]);

  /** 按当前意图类型与 agentCount 自动生成 agent profile */
  const handleAutoGenerate = () => {
    const n = agentCount;
    if (n <= 0) {
      setAgentProfiles([]);
      return;
    }
    const institutions = [...INSTITUTIONS];
    let roles: RoleKey[];
    if (intentType === "hybrid") {
      roles = Array.from({ length: n }, (_, i) => ROLE_KEYS[i % ROLE_KEYS.length]);
    } else {
      const main = intentType.charAt(0).toUpperCase() + intentType.slice(1) as RoleKey;
      roles = Array.from({ length: n }, () => main);
    }
    const next = roles.map((role, i) => ({
      role,
      institution: institutions[i % institutions.length],
    }));
    setAgentProfiles(next);
    message.success("Profiles generated. Edit as needed.");
  };

  const getFileName = (f: File): string => {
    const path = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name || "";
    return path.split(/[/\\]/).pop() ?? path;
  };

  const processUploadedFiles = async (files: File[]) => {
    if (files.length === 0) {
      message.error("No files received. Select folder again.");
      return;
    }
    const chartSpec = files.find((f) => getFileName(f) === "chart_spec.json");
    const metadata = files.find((f) => getFileName(f) === "metadata.json");
    const dataCsv = files.find((f) => getFileName(f) === "data.csv");
    const image = files.find((f) => {
      const name = getFileName(f).toLowerCase();
      return f.type.startsWith("image/") || /\.(svg|png|jpe?g|gif|webp)$/.test(name);
    });
    if (!chartSpec || !metadata) {
      message.error("Folder must contain chart_spec.json and metadata.json.");
      return;
    }
    // 从 metadata.json 自动填入「对图表的理解」
    try {
      const text = await metadata.text();
      const parsed = JSON.parse(text) as { meta?: { description?: string }; description?: string };
      const metaDesc = parsed?.meta?.description ?? parsed?.description ?? "";
      if (metaDesc) setDescription(metaDesc);
    } catch {
      // 解析失败则保留当前描述，不覆盖
    }
    // 一旦用户重新上传新可视化，立即清空传播面板，等点击「开始模拟」后再生成新传播树
    setCaseRef(null);
    setTree(null);
    setAgentLog([]);
    setSummary(null);
    setOverallVariantDescription("");
    setPathOffsetTrend([]);
    setSelectedNode(null);
    setVariantImageUrl(null);
    setStatus("idle");
    if (image) {
      const localPreviewUrl = URL.createObjectURL(image);
      setPreview({
        file: image,
        dataUrl: localPreviewUrl,
        description: description || undefined,
      });
      setOriginalImageUrl(localPreviewUrl);
    } else {
      setPreview(null);
      setOriginalImageUrl(null);
    }

    setUploadingCase(true);
    // 仅跑前端、不连后端时：设置 VITE_USE_MOCK=true 可跳过上传请求，不再触发代理 ECONNREFUSED
    if (import.meta.env.VITE_USE_MOCK === "true") {
      setCaseRef(LOCAL_DEMO_CASE_REF);
      message.info("Local demo. Click Start Simulation to view demo.");
      setUploadingCase(false);
      return;
    }
    try {
      const result = await uploadCase({
        chart_spec: chartSpec,
        metadata: metadata,
        data: dataCsv,
        image,
      });
      const ref = result.caseRef ?? result.chartSpecRef;
      if (!ref) {
        message.warning("Upload did not return caseRef. Check /api/upload-case.");
        setUploadingCase(false);
        return;
      }
      setCaseRef(ref);
      if (result.imageRef && image) {
        setPreview((prev) =>
          prev ? { ...prev, dataUrl: result.imageRef! } : null
        );
        setOriginalImageUrl(result.imageRef);
      }
      message.success("Upload done. Click Start Simulation.");
    } catch {
      // 默认保持后端联调模式，避免静默切到本地 mock 导致“看起来连上了其实没连上”。
      setCaseRef(null);
      message.error("Upload failed. Check backend /api/upload-case and retry.");
    }
    setUploadingCase(false);
  };

  /** 从 agentProfiles 推导 agentCategories（role 与 codebook 四角色一致，直接对应） */
  const getCategoriesForSubmit = (): AgentCategory[] => {
    const roleToCategory: Record<RoleKey, AgentCategory> = {
      Bridger: "Bridger",
      Extender: "Analyst",
      Adverser: "Adverser",
      Amplifier: "Amplifier",
    };
    return agentProfiles.slice(0, agentCount).map((p) => (p.role ? roleToCategory[p.role] : "Bridger"));
  };

  const runMockTreeAndFinish = () => {
    setTimeout(() => {
      appendLog({
        time: "00:00:02",
        source: "SYSTEM",
        message: "Initializing simulation, loading source...",
      });
      appendLog({
        time: "00:00:12",
        source: "CLIMATE_TRUTH",
        message:
          "Agent #2 (Amplifier) used 1998-2012 range, removed source attribution.",
        offsetLevel: "major",
      });
      appendLog({
        time: "00:00:15",
        source: "CLIMATE_TRUTH",
        message:
          'High offset: added trend note "No warming in 15 years", level: major.',
        offsetLevel: "major",
      });
      appendLog({
        time: "00:00:22",
        source: "REDDIT_USER",
        message:
          "Agent #4 (Anxiety) forwarded @ClimateTruth, added anxiety comment, offset: sig.",
        offsetLevel: "sig",
      });
    }, 500);
  };

  const runSimulation = async () => {
    const useLocalDemo = !caseRef || caseRef === LOCAL_DEMO_CASE_REF;
    if (useLocalDemo) {
      message.warning(caseRef === LOCAL_DEMO_CASE_REF ? "Using local demo" : "No case uploaded; using demo");
      setStatus("running");
      setAgentLog([]);
      setTree(null);
      setSummary(null);
      setOverallVariantDescription("");
      setPathOffsetTrend([]);
      appendLog({
        time: "00:00:00",
        source: "SYSTEM",
        message: "Initializing simulation, loading source...",
      });
      runMockTreeAndFinish();
      await new Promise((r) => setTimeout(r, 800));
      applyMockTree();
      setStatus("done");
      return;
    }
    setStatus("running");
    setAgentLog([]);
    setTree(null);
    setSummary(null);
    setOverallVariantDescription("");
    setPathOffsetTrend([]);
    appendLog({
      time: "00:00:00",
      source: "SYSTEM",
      message: "Initializing simulation, loading source...",
    });
    message.loading({ content: "Requesting backend...", key: "sim", duration: 0 });

    let data: Awaited<ReturnType<typeof startSimulation>> | null = null;
    try {
      const effectiveCount = Math.max(1, agentCount);
      const effectiveDepth = Math.max(1, maxDepth);
      const profiles = agentProfiles.slice(0, effectiveCount).map((p) => ({
        role: p.role ?? "Bridger",
        institution: p.institution ?? "",
      }));
      data = await startSimulation({
        agentCount: effectiveCount,
        agentCategories: getCategoriesForSubmit(),
        agentProfiles: profiles,
        maxDepth: effectiveDepth,
        description: description || undefined,
        caseRef,
      });
    } catch {
      message.destroy("sim");
      message.error("Simulation request failed. Check backend logs and request params.");
      setStatus("error");
      return;
    }
    message.destroy("sim");

    if (data?.tree && data?.agentLog !== undefined) {
      message.destroy("sim");
      setTree(data.tree);
      setAgentLog(
        data.agentLog.map((e, i) => ({ ...e, id: e.id || `log-${i}` }))
      );
      if (data.summary) setSummary(data.summary);
      if (data.pathOffsetTrend) setPathOffsetTrend(data.pathOffsetTrend);
      if (data.overallVariantDescription)
        setOverallVariantDescription(data.overallVariantDescription);
      if (data.variantImageUrl) setVariantImageUrl(data.variantImageUrl);
      setStatus("done");
      message.success("Simulation complete.");
      return;
    }

    runMockTreeAndFinish();
    await new Promise((r) => setTimeout(r, 800));
    applyMockTree();
    setStatus("done");
  };

  const applyMockTree = () => {
    setTree({
      nodes: [
        { id: "SRC", label: "NOAA global temperature anomaly chart", actionLabel: "Source", nodeType: "neutral", offset: "none" },
        { id: "V1", label: "BBC News", actionLabel: "News repost", nodeType: "authority", platform: "longform" },
        {
          id: "V2",
          label: "@ClimateTruth",
          actionLabel: "Counter skeptic",
          role: "Adverser",
          nodeType: "adverser",
          platform: "shortform",
          offset: "major",
          operations: [
            "DATA Adverser used 2010-2015 range, highlighted decline, countered warming narrative.",
            "TEXT Adverser removed NOAA attribution, added note \"No warming in 15 years\".",
            "VISUAL None",
          ],
          imageUrl: preview?.dataUrl ?? undefined,
        },
        { id: "V3", label: "NASA Climate", actionLabel: "Science cite", nodeType: "authority", platform: "longform" },
        {
          id: "V4",
          label: "Reddit user",
          actionLabel: "Community repost",
          nodeType: "anxiety",
          platform: "community",
          offset: "sig",
          operations: ["VISUAL forward"],
        },
        {
          id: "V5",
          label: "Weibo user",
          actionLabel: "Cross-lingual",
          nodeType: "mobilizer",
          platform: "shortform",
          operations: ["VISUAL style"],
        },
        { id: "V6", label: "Final node", actionLabel: "Summarize", nodeType: "bridger", platform: "longform", operations: ["VISUAL summarize"] },
      ],
      edges: [
        { id: "e1", source: "SRC", target: "V1" },
        { id: "e2", source: "SRC", target: "V2", offset: "major" },
        { id: "e3", source: "SRC", target: "V3" },
        { id: "e4", source: "V2", target: "V4", offset: "sig" },
        { id: "e5", source: "V2", target: "V5" },
        { id: "e6", source: "V4", target: "V6" },
      ],
      nodeCount: 7,
      edgeCount: 6,
      maxDepth: 3,
      highestOffsetPath: "SRC->V2 (major)",
      topologyType: "tree",
    });

    setPathOffsetTrend([
      { step: "SRC", offset: "none" },
      { step: "V2", offset: "major" },
    ]);
    setOverallVariantDescription(
      "Used 1998-2012 range (hiatus), removed NOAA attribution, added trend note \"No warming in 15 years\". Global warming trend selectively obscured."
    );
    setVariantImageUrl(preview?.dataUrl ?? null);
    setSummary({
      agentCount: 5,
      edgeCount: 5,
      highestOffset: "major",
    });
    setStatus("done");
    message.success("Simulation complete.");
  };

  const s = panel1.spacing;
  return (
    <PanelCard
      style={{ fontFamily: panel1.font.family, flex: "0 0 auto", minHeight: 0 }}
      bodyStyle={{ display: "flex", flexDirection: "column", flex: "0 0 auto", minHeight: 0, overflow: "visible", padding: `${s.section}px ${s.panelPaddingX}px` }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 0, flex: "0 0 auto", minHeight: 0, overflow: "visible" }}>
        <input
          ref={dirInputRef}
          type="file"
          // @ts-expect-error webkitdirectory is widely supported
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            const list = e.target.files;
            if (!list || list.length === 0) return;
            const fileArray = Array.from(list);
            processUploadedFiles(fileArray);
            e.target.value = "";
          }}
        />
        {/* 上传文件：与右侧预览框一致 - 内部 F4F5F7，内嵌虚线边框 BDC9D1 */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => !uploadingCase && dirInputRef.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && !uploadingCase && dirInputRef.current?.click()}
          style={{
            flexShrink: 0,
            height: panel1.sizes.uploadHeight,
            borderRadius: panel1.sizes.uploadRadius,
            background: panel1.colors.uploadBg,
            outline: panel1.colors.insetBorder,
            outlineOffset: panel1.sizes.insetBorderOffset,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            cursor: uploadingCase ? "not-allowed" : "pointer",
            opacity: uploadingCase ? 0.6 : 1,
          }}
        >
          <img src={uploadIcon} alt="" style={{ width: 24, height: 24, objectFit: "contain" }} />
          <span style={{ fontSize: panel1.font.body, color: panel1.colors.uploadText, fontWeight: 700 }}>Upload</span>
        </div>

        {/* 预览：与右侧预览框一致 - 内部 F4F5F7，内嵌虚线边框 BDC9D1；整体上移 3px；标题下间距紧凑 */}
        <div style={{ marginTop: s.section - 3, flexShrink: 0 }}>
          <div style={{ marginBottom: s.blockSmall, fontSize: panel1.font.label, fontWeight: 700, color: panel1.colors.label }}>Preview</div>
          <div
            style={{
              width: "100%",
              height: panel1.sizes.previewMinHeight,
              minHeight: panel1.sizes.previewMinHeight,
              maxHeight: panel1.sizes.previewMinHeight,
              borderRadius: panel1.sizes.uploadRadius,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: panel1.colors.previewBg,
              outline: panel1.colors.insetBorder,
              outlineOffset: panel1.sizes.insetBorderOffset,
              overflow: "hidden",
            }}
          >
            {preview?.dataUrl ? (
              <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <img
                src={preview.dataUrl}
                alt="Preview"
                  style={{ maxWidth: "100%", maxHeight: "100%", width: "auto", height: "auto", objectFit: "contain" }}
              />
              </div>
            ) : (
              <span style={{ color: panel1.colors.secondary, fontSize: panel1.font.body }}>No preview</span>
            )}
          </div>
        </div>

        {/* 图表理解输入框（仅保留框，无标题占位）；紧凑间距 */}
        <div style={{ marginTop: s.blockSmall, flexShrink: 0 }}>
          <Input.TextArea
            rows={1}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. NOAA annual temp anomaly, x 1880-2023, y anomaly 1.5°C"
            style={{
              minHeight: panel1.sizes.descMinHeight,
              resize: "none",
              border: `1px solid ${panel1.colors.descBorder}`,
              borderRadius: panel1.sizes.uploadRadius,
              background: "#FFFFFF",
              fontFamily: panel1.font.family,
              fontSize: panel1.font.body,
            }}
          />
        </div>

        {/* 分割线：整体上移，为 Agent 池留出更多空间 */}
        <div
          style={{
            flexShrink: 0,
            marginTop: s.blockSmall,
            height: 0,
            borderTop: `${panel1.borders.dividerWeight}px solid ${panel1.colors.divider}`,
          }}
        />

        {/* 环境参数：滑动条区域高度缩小，为下方 Agent Profile 留出更多空间 */}
        <div style={{ marginTop: s.blockSmall, flexShrink: 0 }}>
          <div style={{ marginBottom: s.blockSmall, fontSize: panel1.font.label, fontWeight: 700, color: panel1.colors.label }}>Environment parameters</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div>
              <div style={{ marginBottom: 2, fontSize: 12, fontWeight: 700, color: panel1.colors.envParamLabel }}>Max depth {maxDepth}</div>
              <div style={{ background: panel1.colors.envPanelBg, borderRadius: 4, padding: "0 8px", height: panel1.sizes.sliderRowHeight, display: "flex", alignItems: "center" }}>
                <div className="setup-panel-slider-wrap" style={{ width: "100%" }}>
                  <Slider
                    className="setup-panel-slider"
                    min={0}
                    max={5}
                    value={maxDepth}
                    onChange={setMaxDepth}
                    styles={{
                      track: { background: panel1.colors.sliderFilled },
                      rail: { background: panel1.colors.sliderTrack },
                      handle: {
                        width: panel1.sizes.sliderThumb,
                        height: panel1.sizes.sliderThumb,
                        border: "none",
                        background: "transparent",
                        borderRadius: "50%",
                      },
                    }}
                  />
                </div>
              </div>
            </div>
            <div>
              <div style={{ marginBottom: 2, fontSize: 12, fontWeight: 700, color: panel1.colors.envParamLabel }}>Agents {agentCount}</div>
              <div style={{ background: panel1.colors.envPanelBg, borderRadius: 4, padding: "0 8px", height: panel1.sizes.sliderRowHeight, display: "flex", alignItems: "center" }}>
                <div className="setup-panel-slider-wrap" style={{ width: "100%" }}>
                  <Slider
                    className="setup-panel-slider"
                    min={0}
                    max={6}
                    value={agentCount}
                    onChange={setAgentCount}
                    styles={{
                      track: { background: panel1.colors.sliderFilled },
                      rail: { background: panel1.colors.sliderTrack },
                      handle: {
                        width: panel1.sizes.sliderThumb,
                        height: panel1.sizes.sliderThumb,
                        border: "none",
                        background: "transparent",
                        borderRadius: "50%",
                      },
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Agent Profile：快速生成配置框 与 Agent 池框；高度随内容，整列滚动；紧凑间距以让整页在框内完整显示 */}
        <div style={{ marginTop: s.blockSmall, flex: "0 1 auto", minHeight: 0, display: "flex", flexDirection: "column", overflow: "visible", isolation: "isolate", zIndex: 2 }}>
          <div style={{ marginBottom: s.blockSmall, flexShrink: 0, fontSize: panel1.font.label, fontWeight: 700, color: panel1.colors.label }}>Agent profile</div>

          {/* 快速生成配置：独立框，内含五选项两行 + Auto Generate 按钮 */}
          <div
            style={{
              border: `1px solid ${panel1.colors.agentPoolBorder}`,
              borderRadius: panel1.sizes.uploadRadius,
              background: "#FBFBFB",
              flexShrink: 0,
              padding: s.blockSmall,
            }}
          >
            <div style={{ marginBottom: s.blockSmall, fontSize: panel1.font.body, fontWeight: 600, color: panel1.colors.envParamLabel }}>Quick setup</div>
            <div style={{ display: "flex", flexWrap: "nowrap", gap: 6, marginBottom: s.blockSmall, width: "100%" }}>
              {INTENT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setIntentType(opt.value)}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    padding: "6px 8px",
                    borderRadius: 8,
                    border: "1px solid #A8AEB7",
                    boxSizing: "border-box",
                    background: intentType === opt.value ? panel1.colors.agentCardSelectedBg : "#FFF",
                    color: panel1.colors.label,
                    fontSize: panel1.font.body,
                    fontWeight: 600,
                    fontFamily: panel1.font.family,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={handleAutoGenerate}
              style={{
                width: "100%",
                height: panel1.sizes.autoGenerateButtonHeight,
                borderRadius: panel1.sizes.uploadRadius,
                background: "#616975",
                border: "none",
                color: "#FFFFFF",
                fontSize: panel1.font.body,
                fontWeight: 700,
                fontFamily: panel1.font.family,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              <img src={generateIcon} alt="" style={{ width: 18, height: 18, objectFit: "contain" }} />
              Auto Generate
            </button>
          </div>

          {/* Agent 池：固定高度，底线下移以放大框；内部滚动；内背景 FBFBFB；增加高度以扩大可编辑区域，间距转为池高以保持 Start Simulation 按钮位置不变 */}
          <div
            style={{
              marginTop: s.blockSmall,
              marginBottom: 0,
              border: `1px solid ${panel1.colors.agentPoolBorder}`,
              borderRadius: panel1.sizes.uploadRadius,
              background: "#FBFBFB",
              height: panel1.sizes.agentCardHeight + s.block + 24 + 24 + 49 + 54,
              minWidth: 0,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              position: "relative",
              zIndex: 3,
              flexShrink: 0,
              isolation: "isolate",
            }}
          >
            <div
              style={{
                padding: s.blockSmall,
                paddingBottom: 24,
                display: "block",
                overflowY: "auto",
                height: "100%",
                boxSizing: "border-box",
              }}
            >
            {Array.from({ length: agentCount }, (_, i) => {
              const profile: AgentProfileEntry = agentProfiles[i] ?? { role: null, institution: null };
              const isEditing = editingProfileIndex === i;
              const isSet = !!profile.role;
              const color = profile.role ? ROLE_COLORS[profile.role] : GREY_ICON;
              const cardBorder = isEditing
                ? "#A8AEB7"
                : isSet
                  ? color
                  : GREY_BORDER;
              const cardBg = isEditing ? "#F6F6F6" : isSet ? "#FFFFFF" : GREY_BG;
              return (
                <div
                  key={i}
                  style={{
                    minHeight: panel1.sizes.agentCardHeight,
                    display: "flex",
                    alignItems: isEditing ? "stretch" : "center",
                    flexDirection: isEditing ? "column" : "row",
                    gap: 10,
                    padding: "8px 12px",
                    marginBottom: i < agentCount - 1 ? s.blockSmall : 0,
                    borderRadius: panel1.sizes.uploadRadius,
                    border: `2px solid ${cardBorder}`,
                    background: cardBg,
                  }}
                >
                  {isEditing ? (
                    <>
                      {/* 编辑态：左上角 robot icon + 当前角色名与功能介绍（与圆形 icon 垂直居中对齐）→ 四角色 → 平台 → 完成 */}
                      <div style={{ display: "flex", alignItems: "center", gap: 3, marginBottom: 0 }}>
                        <div
                          style={{
                            width: panel1.sizes.agentCircle,
                            height: panel1.sizes.agentCircle,
                            borderRadius: "50%",
                            background: color,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                          }}
                        >
                          <img src={robotIcon} alt="" style={{ width: panel1.sizes.agentIconInCircle, height: panel1.sizes.agentIconInCircle, objectFit: "contain" }} />
                        </div>
                        {profile.role && (
                          <div style={{ flex: 1, minWidth: 0, fontSize: 14, lineHeight: 1.3 }}>
                            <span style={{ fontWeight: 700, color: "#353536" }}>{profile.role}</span>
                            <span style={{ color: "#697281" }}> ： {ROLE_DESCRIPTIONS[profile.role]}</span>
                          </div>
                        )}
                      </div>
                      {/* 四个角色横排：框内 #F6F6F6，内线 #CCD8E7 1px；icon 下圆形为角色对应色 */}
                      <div style={{ display: "flex", gap: 2, marginBottom: 1, width: "100%" }}>
                        {ROLES.map((r) => {
                          return (
                            <button
                              key={r.value}
                              type="button"
                              onClick={() =>
                                setAgentProfiles((prev) => {
                                  const next = prev.slice();
                                  while (next.length <= i) next.push({ role: null, institution: null });
                                  next[i] = { ...next[i], role: r.value };
                                  return next;
                                })
                              }
                              style={{
                                flex: 1,
                                minWidth: 0,
                                height: 64,
                                borderRadius: 10,
                                border: "2px solid #CCD8E7",
                                background: "#F6F6F6",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 4,
                                cursor: "pointer",
                                fontFamily: panel1.font.family,
                                padding: 0,
                              }}
                            >
                              <span
                                style={{
                                  width: 28,
                                  height: 28,
                                  borderRadius: "50%",
                                  background: ROLE_COLORS[r.value],
                                  display: "inline-flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                }}
                              >
                                <img
                                  src={robotIcon}
                                  alt=""
                                  style={{
                                    width: 18,
                                    height: 18,
                                    objectFit: "contain",
                                    filter: "brightness(0) invert(1)",
                                  }}
                                />
                              </span>
                              <span
                                style={{
                                  fontSize: 12,
                                  fontWeight: 600,
                                  color: "#697281",
                                  lineHeight: 1.2,
                                }}
                              >
                                {r.value}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                      {/* 平台菜单框：外层单一边框 #CCD8E7，Select 无边框去内线 */}
                      <div
                        className="setup-panel-platform-select-wrap"
                        style={{
                          marginBottom: 0,
                          height: 35,
                          borderRadius: panel1.sizes.uploadRadius,
                          border: "1px solid #CCD8E7",
                          overflow: "hidden",
                        }}
                      >
                        <Select
                          variant="borderless"
                          className="setup-panel-platform-select"
                          placeholder="Institution / platform"
                          value={profile.institution}
                          onChange={(v) =>
                            setAgentProfiles((prev) => {
                              const next = prev.slice();
                              while (next.length <= i) next.push({ role: null, institution: null });
                              next[i] = { ...next[i], institution: v };
                              return next;
                            })
                          }
                          style={{
                            width: "100%",
                            fontSize: panel1.font.body,
                            height: 35,
                            minHeight: 35,
                          }}
                          options={INSTITUTIONS.map((inst) => ({ value: inst, label: inst }))}
                        />
                      </div>
                      {/* 完成按钮：W65 H35，略上移；减小与底部边框的间隙 */}
                      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -4, marginBottom: -2 }}>
                        <button
                          type="button"
                          onClick={() => setEditingProfileIndex(-1)}
                          style={{
                            width: 65,
                            height: 35,
                            padding: 0,
                            borderRadius: 10,
                            background: "#495058",
                            color: "#FFFFFF",
                            fontSize: panel1.font.body,
                            fontWeight: 600,
                            fontFamily: panel1.font.family,
                            border: "none",
                            boxShadow: "inset 0 0 0 1px #CCD8E7",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          Done
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div
                        style={{
                          width: panel1.sizes.agentCircle,
                          height: panel1.sizes.agentCircle,
                          borderRadius: "50%",
                          background: color,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        <img src={robotIcon} alt="" style={{ width: panel1.sizes.agentIconInCircle, height: panel1.sizes.agentIconInCircle, objectFit: "contain" }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#353536", lineHeight: 1.3 }}>
                          {profile.role ?? "null"}
                        </div>
                        <div style={{ fontSize: 12, color: "#697281", marginTop: 2, lineHeight: 1.4 }}>
                          Platform: {profile.institution ?? "null"}
                        </div>
                      </div>
                      <EditOutlined
                        style={{ color: panel1.colors.secondary, fontSize: 14, cursor: "pointer" }}
                        onClick={() => setEditingProfileIndex(i)}
                      />
                    </>
                  )}
                </div>
              );
            })}
                <div style={{ height: 16, minHeight: 16 }} aria-hidden="true" />
              </div>
          </div>
        </div>

        {/* 间隔与按钮置于 Agent 池层级之下，不遮挡池底；间距缩小以保持开始模拟按钮位置不变 */}
        <div style={{ height: 0, minHeight: 0, flexShrink: 0, position: "relative", zIndex: 0 }} aria-hidden="true" />

        <Button
          type="primary"
          block
          loading={status === "running"}
          onClick={runSimulation}
          style={{
            flexShrink: 0,
            marginTop: 9,
            height: panel1.sizes.startButtonHeight,
            background: panel1.colors.startButton,
            borderColor: panel1.colors.startButton,
            borderRadius: panel1.sizes.uploadRadius,
            fontSize: panel1.font.label,
            fontWeight: 700,
            fontFamily: panel1.font.family,
            color: "#FFFFFF",
          }}
        >
          Start Simulation
        </Button>

      </div>
    </PanelCard>
  );
}
