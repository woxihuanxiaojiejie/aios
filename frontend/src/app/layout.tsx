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
            { key: "/dashboard", label: <Link to="/dashboard">Dashboard</Link> },
            { key: "/research", label: <Link to="/research">Research</Link> },
            { key: "/executions", label: <Link to="/executions">Executions</Link> },
            { key: "/settlements", label: <Link to="/settlements">Settlements</Link> },
            {
              key: "/learning-proposals",
              label: <Link to="/learning-proposals">Learning Proposals</Link>,
            },
          ]}
        />
      </Header>
      <Content className="aios-content">{children}</Content>
    </Layout>
  );
}

function selectedNavKey(pathname: string) {
  if (pathname.startsWith("/dashboard")) return "/dashboard";
  if (pathname.startsWith("/executions")) return "/executions";
  if (pathname.startsWith("/settlements")) return "/settlements";
  if (pathname.startsWith("/learning-proposals")) return "/learning-proposals";
  if (pathname.startsWith("/research")) return "/research";
  return "/dashboard";
}
