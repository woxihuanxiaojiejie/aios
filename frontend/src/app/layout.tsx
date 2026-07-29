import { Layout, Menu, Typography } from "antd";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

const { Header, Content } = Layout;

export function AppLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const selectedKey = selectedNavKey(location.pathname);

  return (
    <Layout className="aios-shell">
      <Header className="aios-header">
        <Typography.Title level={1} className="aios-title">
          AIOS
        </Typography.Title>
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          className="aios-nav"
          items={[
            { key: "/dashboard", label: <Link to="/dashboard">首页</Link> },
            { key: "/research", label: <Link to="/research">研究</Link> },
            { key: "/decisions", label: <Link to="/decisions">决策</Link> },
            { key: "/reviews", label: <Link to="/reviews">复盘</Link> },
            { key: "/learning", label: <Link to="/learning">学习</Link> },
            { key: "/system", label: <Link to="/system">系统</Link> },
          ]}
        />
      </Header>
      <Content className="aios-content">{children}</Content>
    </Layout>
  );
}

function selectedNavKey(pathname: string) {
  if (pathname.startsWith("/dashboard")) return "/dashboard";
  if (pathname.startsWith("/decisions")) return "/decisions";
  if (pathname.startsWith("/reviews")) return "/reviews";
  if (pathname.startsWith("/executions")) return "/reviews";
  if (pathname.startsWith("/settlements")) return "/reviews";
  if (pathname.startsWith("/learning")) return "/learning";
  if (pathname.startsWith("/system")) return "/system";
  if (pathname.startsWith("/research")) return "/research";
  return "/dashboard";
}
