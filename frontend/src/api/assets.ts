import { get } from "./client";
import { AssetOutSchema } from "./schemas";
import type { AssetOut } from "./schemas";

export function listAssets(): Promise<AssetOut[]> {
  return get("/assets", AssetOutSchema.array());
}
