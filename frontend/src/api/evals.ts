import { post } from "./client";
import { EvalRunOutSchema } from "./schemas";
import type { EvalRunOut, EvalRunRequest } from "./schemas";

export function runEval(body: EvalRunRequest): Promise<EvalRunOut> {
  return post("/evals/run", body, EvalRunOutSchema);
}
