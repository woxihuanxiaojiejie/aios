import { useNavigate } from "react-router-dom";

import { ResearchWorkbench } from "../ResearchWorkbench";

export function ResearchNewPage() {
  const navigate = useNavigate();
  return (
    <ResearchWorkbench
      onRunCreated={(runId) => navigate(`/research/${encodeURIComponent(runId)}`)}
    />
  );
}
