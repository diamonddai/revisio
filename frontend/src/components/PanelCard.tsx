import { Card } from "antd";
import type { PropsWithChildren, ReactNode, CSSProperties } from "react";

type Props = PropsWithChildren<{
  title?: ReactNode;
  extra?: ReactNode;
  bodyStyle?: CSSProperties;
  style?: CSSProperties;
}>;

export default function PanelCard({
  title,
  extra,
  children,
  style,
  bodyStyle,
}: Props) {
  return (
    <Card
      title={title}
      extra={extra}
      style={{
        width: "100%",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "none",
        boxShadow: "none",
        ...style,
      }}
      bodyStyle={{
        flex: 1,
        minHeight: 0,
        padding: "18px 20px",
        overflow: "auto",
        ...bodyStyle,
      }}
    >
      {children}
    </Card>
  );
}
