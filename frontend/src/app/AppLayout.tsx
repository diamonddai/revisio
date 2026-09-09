import { Layout } from "antd";
import { SimulationProvider } from "../context/simulation";
import SetupPanel from "../features/setup/SetupPanel";
import PropagationPanel from "../features/propagation/PropagationPanel";
import OffsetPanel from "../features/offset/OffsetPanel";

const { Content } = Layout;

/** 底板：整页底板，设计稿参考尺寸 1821×1101，颜色 EDEFF2 */
const BOARD_COLOR = "#EDEFF2";

/** 左栏与右栏等宽；标题条适量缩小，下方面板拉高以显示更多信息 */
const PANEL1_X = 22;
const SETUP_PANEL_HEADER_H = 44;
const CONTENT_PANEL_RADIUS = 10;
const SETUP_PANEL_COLOR = "#808993";
const HEADER_CONTENT_GAP = 12;
const TOP_PADDING = 12;

/** 左侧面板内容等比例缩小，便于一屏内看到 5 个 Agent 且保持相对位置 */
const SETUP_PANEL_SCALE = 0.88;

const COL_TEMPLATE = "minmax(360px, 1fr) minmax(420px, 2.2fr) minmax(360px, 1fr)";

export default function AppLayout() {
  return (
    <SimulationProvider>
      <Layout style={{ height: "100vh", display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
        {/* 底板：整页铺满（100%×100%），颜色 EDEFF2，三栏布局在其内 */}
        <Content
          style={{
            flex: 1,
            minHeight: 0,
            overflow: "hidden",
            width: "100%",
            height: "100%",
            padding: 0,
            margin: 0,
            background: BOARD_COLOR,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* 三栏标题条：左中右等分栅格，#808993；标题与下方白板之间留空隙 */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: COL_TEMPLATE,
              gap: 16,
              paddingLeft: PANEL1_X,
              paddingTop: TOP_PADDING,
              paddingRight: 24,
              paddingBottom: 0,
              flexShrink: 0,
            }}
          >
            <div
              style={{
                height: SETUP_PANEL_HEADER_H,
                background: SETUP_PANEL_COLOR,
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-start",
                paddingLeft: 16,
                borderRadius: 0,
                fontFamily: "'Inria Sans', sans-serif",
                fontWeight: 700,
                fontSize: 16,
              }}
            >
              Setting
            </div>
            <div
              style={{
                height: SETUP_PANEL_HEADER_H,
                background: SETUP_PANEL_COLOR,
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-start",
                paddingLeft: 16,
                borderRadius: 0,
                fontFamily: "'Inria Sans', sans-serif",
                fontWeight: 700,
                fontSize: 16,
              }}
            >
              Simulation
            </div>
            <div
              style={{
                height: SETUP_PANEL_HEADER_H,
                background: SETUP_PANEL_COLOR,
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-start",
                paddingLeft: 16,
                borderRadius: 0,
                fontFamily: "'Inria Sans', sans-serif",
                fontWeight: 700,
                fontSize: 16,
              }}
            >
              Analysis
            </div>
          </div>

          {/* 三栏内容区：标题与白板之间留空隙 HEADER_CONTENT_GAP */}
          <div
            style={{
              flex: 1,
              minHeight: 0,
              display: "grid",
              gridTemplateColumns: COL_TEMPLATE,
              gridTemplateRows: "1fr",
              gap: 16,
              alignItems: "stretch",
              marginTop: HEADER_CONTENT_GAP,
              paddingLeft: PANEL1_X,
              paddingRight: 24,
              paddingBottom: 12,
            }}
          >
            <div
              style={{
                minHeight: 0,
                display: "flex",
                flexDirection: "column",
                background: "#fff",
                borderRadius: CONTENT_PANEL_RADIUS,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflowX: "hidden",
                  overflowY: "hidden",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div
                  style={{
                    width: `${100 / SETUP_PANEL_SCALE}%`,
                    minHeight: "100%",
                    transform: `scale(${SETUP_PANEL_SCALE})`,
                    transformOrigin: "top left",
                    display: "flex",
                    flexDirection: "column",
                    flexShrink: 0,
                  }}
                >
                  <SetupPanel />
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                minHeight: 0,
                background: "#fff",
                borderRadius: "var(--radius-lg)",
                padding: "16px 0",
                overflow: "hidden",
              }}
            >
              <PropagationPanel />
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                minHeight: 0,
                background: "#fff",
                borderRadius: "var(--radius-lg)",
                padding: 16,
                overflowX: "visible",
                overflowY: "hidden",
              }}
            >
              <OffsetPanel />
            </div>
          </div>
        </Content>
      </Layout>
    </SimulationProvider>
  );
}
