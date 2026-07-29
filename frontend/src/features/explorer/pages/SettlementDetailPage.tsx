import { useQuery } from "@tanstack/react-query";
import { Button, Space, Typography } from "antd";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../infrastructure/api/client";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/researchDisplay";
import { explorerApi } from "../api";
import { ChainSections, IdText } from "./common";

export function SettlementDetailPage() {
  const { settlementId } = useParams();
  const detail = useQuery({
    queryKey: ["settlement-detail", settlementId],
    queryFn: () => explorerApi.settlementDetail(settlementId!),
    enabled: Boolean(settlementId),
  });

  if (detail.isLoading) return <LoadingState />;
  if (detail.error) return <ErrorState message={errorMessage(detail.error)} />;
  if (!detail.data) return <EmptyState description="Settlement 不存在" />;

  return (
    <section className="research-detail-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={2}>Settlement Detail</Typography.Title>
          <IdText value={detail.data.settlement?.outcome_id} />
        </div>
        <Space>
          <Link to="/settlements"><Button>Back</Button></Link>
          {detail.data.simulated_execution ? (
            <Link
              to={`/executions/${encodeURIComponent(detail.data.simulated_execution.execution_id)}`}
            >
              <Button type="primary">Execution</Button>
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
