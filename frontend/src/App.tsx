/** 应用壳：侧边导航 + 路由表。 */
import { Layout, Menu, Typography } from "antd";
import {
  CommentOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  ApartmentOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { AskPage } from "./features/ask/AskPage";
import { SemanticPage } from "./features/semantic/SemanticPage";
import { AssetsPage } from "./features/assets/AssetsPage";
import { TracesPage } from "./features/traces/TracesPage";
import { EvalsPage } from "./features/evals/EvalsPage";

const { Sider, Content } = Layout;

const MENU = [
  { key: "/ask", icon: <CommentOutlined />, label: "问数分析" },
  { key: "/semantic", icon: <DatabaseOutlined />, label: "语义层" },
  { key: "/assets", icon: <ApartmentOutlined />, label: "技能与工具" },
  { key: "/traces", icon: <BarChartOutlined />, label: "执行追踪" },
  { key: "/evals", icon: <ExperimentOutlined />, label: "评测看板" },
];

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const selected = MENU.find((m) => location.pathname.startsWith(m.key))?.key ?? "/ask";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light" width={200} style={{ borderRight: "1px solid #f0f0f0" }}>
        <div style={{ padding: "16px 16px 8px" }}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            DataQnA
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            企业数据智能分析
          </Typography.Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          items={MENU}
          onClick={(e) => navigate(e.key)}
        />
      </Sider>
      <Content style={{ padding: 24, overflow: "auto" }}>
        <Routes>
          <Route path="/" element={<Navigate to="/ask" replace />} />
          <Route path="/ask" element={<AskPage />} />
          <Route path="/semantic" element={<SemanticPage />} />
          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/traces" element={<TracesPage />} />
          <Route path="/evals" element={<EvalsPage />} />
        </Routes>
      </Content>
    </Layout>
  );
}
