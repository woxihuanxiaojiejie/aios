import type {
  Decision,
  Evaluation,
  Learning,
  Outcome,
  ResearchRun,
  ResearchSession,
  Review,
  SimulatedExecution,
} from "../../infrastructure/api/research";

export type LearningDetail = {
  learning: Learning;
  review: Review | null;
  evaluation: Evaluation | null;
  settlement: Outcome | null;
  simulated_execution: SimulatedExecution | null;
  decision: Decision | null;
  research_run: ResearchRun | null;
  research_session: ResearchSession | null;
  current_value_summary: string;
  proposed_value_summary: string;
  change_summary: string;
  technical_details: Record<string, unknown>;
};
