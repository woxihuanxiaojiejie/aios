import { Layout, Menu, Typography } from "antd";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

const { Header, Content } = Layout;

export function AppLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const selectedKey = location.pathname.startsWith("/research")
    ? "/research"
    : "/watchlist";

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
            { key: "/watchlist", label: <Link to="/watchlist">Watchlist</Link> },
            { key: "/research", label: <Link to="/research">Research</Link> },
          ]}
        />
      </Header>
      <Content className="aios-content">{children}</Content>
    </Layout>
  );
}
