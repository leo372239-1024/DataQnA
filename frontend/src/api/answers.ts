import { get } from "./client";
import { AnswerOutSchema } from "./schemas";
import type { AnswerOut } from "./schemas";

export function getAnswer(questionId: string): Promise<AnswerOut> {
  return get(`/answers/${questionId}`, AnswerOutSchema);
}
