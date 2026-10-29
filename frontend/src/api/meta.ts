import { get } from "./client";
import { MetaSchema } from "./schemas";
import type { Meta } from "./schemas";

export function getMeta(): Promise<Meta> {
  return get("/meta", MetaSchema);
}
