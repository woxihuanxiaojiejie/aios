import { useQuery } from "@tanstack/react-query";
import { Button, Space, Typography } from "antd";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../infrastructure/api/client";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/researchDisplay";
import { explorerApi } from "../api";
import { ChainSections, IdText } from "./common";

export function ExecutionDetailPage() {
  const { executionId } = useParams();
  const detail = useQuery({
    queryKey: ["execution-detail", executionId],
    queryFn: () => explorerApi.executionDetail(executionId!),
    enabled: Boolean(executionId),
  });

  if (detail.isLoading) return <LoadingState />;
  if (detail.error) return <ErrorState message={errorMessage(detail.error)} />;
  if (!detail.data) return <EmptyState description="Execution 不存在" />;

  return (
    <section className="research-detail-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>Simulated Execution Detail</Typography.Title>
          <IdText value={detail.data.simulated_execution?.execution_id} />
        </div>
        <Space>
          <Link to="/executions"><Button>Back</Button></Link>
          {detail.data.settlement ? (
            <Link to={`/settlements/${encodeURIComponent(detail.data.settlement.outcome_id)}`}>
              <Button type="primary">Settlement</Button>
            </Link>
          ) : null}
        </Space>
      </div>
      <ChainSections detail={detail.data} />
    </section>
  );
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.readableMessage;
  if (error instanceof Error) return error.message;
  return "Backend request failed";
}
